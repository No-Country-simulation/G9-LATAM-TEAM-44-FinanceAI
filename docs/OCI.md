# Integración con Oracle Cloud Infrastructure

FinanceAI usa **OCI Object Storage** en los dos extremos del ciclo de vida del modelo,
y **OCI Compute** como destino de despliegue.

| Uso | Componente | Qué hace |
|---|---|---|
| Almacenamiento de modelos | `ciencia-datos/oci_storage.py` | El notebook **sube** los artefactos entrenados al bucket |
| Carga de modelos | `srv-python/app/modelos.py` | El ml-service los **descarga** al arrancar |
| Historial de análisis | `srv-java/…/integration/OCIStorageService.java` | El backend **archiva** cada análisis como objeto JSON |
| Alojamiento | `docker-compose.yml` | Los tres contenedores corren en una instancia de OCI Compute |

## Por qué el modelo no viaja dentro de la imagen

El `Dockerfile` de `srv-python` no copia los `.joblib`; el servicio los descarga al arrancar.
Así, publicar un modelo reentrenado es subir un objeto al bucket y reiniciar el contenedor,
sin reconstruir la imagen ni tocar el pipeline de despliegue.

El orden de resolución está en `modelos.py`: OCI → disco local → reglas por palabras clave.
El arranque no falla; si no hay artefactos, el servicio lo declara en `/modelo/info` y
responde con las reglas.

---

## Opción A — Pre-Authenticated Request (la rápida)

Una PAR es una URL firmada con caducidad. No necesita SDK ni credenciales en el contenedor.
Es lo que usa el backend Java y sirve también para el ml-service.

### 1. Crear el bucket

```bash
oci os bucket create \
  --compartment-id <OCID_DEL_COMPARTIMENTO> \
  --name finance-ai-models
```

### 2. Crear la PAR

```bash
# Lectura y escritura sobre todo el bucket, válida 30 días.
oci os preauth-request create \
  --bucket-name finance-ai-models \
  --name financeai-par \
  --access-type AnyObjectReadWrite \
  --time-expires "$(date -u -d '+30 days' +%Y-%m-%dT%H:%M:%SZ)"
```

La respuesta trae `accessUri`. **Se muestra una sola vez**: guárdala en ese momento.
La URL completa es:

```
https://objectstorage.<region>.oraclecloud.com<accessUri>
```

### 3. Configurar

Crea un `.env` en la raíz (está en `.gitignore`):

```bash
OCI_PAR_URL=https://objectstorage.us-ashburn-1.oraclecloud.com/p/XXXX/n/<namespace>/b/finance-ai-models/o/
OCI_BUCKET=finance-ai-models
OCI_NAMESPACE=<tu-namespace>
OCI_REGION=us-ashburn-1
```

`docker compose up` las inyecta en ambos servicios.

Sobre la caducidad: cuando la PAR expira, el ml-service no descarga el modelo y arranca con
los artefactos locales o con reglas. No se cae, pero el aviso solo se ve en `/modelo/info`,
donde `origen` deja de ser `oci`. Para algo de larga vida, usa la opción B.

---

## Opción B — SDK con instance principals (la de producción)

Sin secretos en ninguna parte: la propia instancia de Compute se autentica ante Object
Storage mediante su identidad de IAM.

### 1. Grupo dinámico

Consola → *Identity → Dynamic Groups* → crear `financeai-instances` con la regla:

```
ALL {instance.compartment.id = '<OCID_DEL_COMPARTIMENTO>'}
```

### 2. Política

Consola → *Identity → Policies*:

```
Allow dynamic-group financeai-instances to manage objects in compartment <compartimento> where target.bucket.name = 'finance-ai-models'
```

### 3. Configurar el servicio

```bash
OCI_AUTH=instance_principal
OCI_BUCKET=finance-ai-models
OCI_NAMESPACE=<tu-namespace>
OCI_REGION=us-ashburn-1
```

En local, sin instancia de Compute, usa el archivo de configuración del SDK:

```bash
oci setup config          # genera ~/.oci/config
export OCI_AUTH=config_file
export OCI_PROFILE=DEFAULT
```

---

## Publicar un modelo desde el notebook

La última sección de `notebook.ipynb` lo hace sola:

```python
if oci_storage.configurado():
    for ruta in (ruta_clasificador, ruta_perfil, ruta_metadatos):
        oci_storage.subir(str(ruta), ruta.name)
```

Sin credenciales configuradas, avisa y sigue. Los artefactos quedan en
`ciencia-datos/artefactos/` y el ml-service los toma de ahí.

Manualmente:

```bash
oci os object put --bucket-name finance-ai-models \
  --file ciencia-datos/artefactos/clasificador_gastos.joblib
oci os object put --bucket-name finance-ai-models \
  --file ciencia-datos/artefactos/modelo_perfil.joblib
oci os object put --bucket-name finance-ai-models \
  --file ciencia-datos/artefactos/metadatos.json
```

## Verificar que está funcionando

```bash
curl http://localhost:8000/modelo/info | jq '{origen, version, oci}'
```

```json
{
  "origen": "oci",
  "version": "1.0.0",
  "oci": { "via": "par", "bucket": "finance-ai-models", "region": "us-ashburn-1" }
}
```

`origen` puede ser:

| Valor | Significado |
|---|---|
| `oci` | Descargado del bucket. Es el camino esperado en despliegue. |
| `local` | Tomado de `ciencia-datos/artefactos/`. Normal en desarrollo. |
| `reglas` | Sin artefactos: responde con palabras clave. Revisa `errores` en la misma respuesta. |

Desde el backend, la vista equivalente:

```bash
curl http://localhost:8080/api/v1/ml-status | jq
```

---

## Historial de análisis

Con `OCI_PAR_URL` configurada, cada análisis se archiva en:

```
historial/AAAA/MM/DD/AAAAMMDDTHHMMSS-<id>.json
```

Object Storage no tiene índices, así que la jerarquía por fecha es lo que permite recuperar
después un rango de días sin listar el bucket entero.

La subida es asíncrona y best-effort: si Object Storage no responde, se registra un aviso y
el usuario recibe su análisis igual.

Se guardan el perfil, los agregados por categoría y los indicadores. No se guardan las
descripciones de las transacciones: para analizar la evolución financiera no hacen falta, y
almacenarlas convertiría el bucket en un archivo de hábitos de consumo identificables. Ver
`construirRegistro` en `OCIStorageService.java`.

Para desactivarlo: `OCI_HISTORIAL=false`.

Consultar lo archivado:

```bash
oci os object list --bucket-name finance-ai-models --prefix historial/2026/08/
```

---

## Despliegue en OCI Compute

```bash
# 1. Instancia VM.Standard.E4.Flex (2 OCPU, 8 GB) con Oracle Linux 9
# 2. Abrir los puertos 8080 y 8081 en la security list de la subred
# 3. En la instancia:
sudo dnf install -y docker git
sudo systemctl enable --now docker

git clone <repo> && cd G9-LATAM-TEAM-44-FinanceAI
cat > .env <<'EOF'
OCI_AUTH=instance_principal
OCI_BUCKET=finance-ai-models
OCI_NAMESPACE=<namespace>
OCI_REGION=us-ashburn-1
EOF

sudo docker compose up -d --build
```

Con instance principals no hay ninguna credencial en el disco de la instancia.

## Resolución de problemas

| Síntoma | Causa probable |
|---|---|
| `origen: "reglas"` y `errores` menciona joblib | Falta `scikit-learn` en la imagen, o su versión no coincide con la del entrenamiento |
| `origen: "local"` teniendo OCI configurado | La descarga falló: revisa los logs del ml-service; suele ser la PAR caducada |
| 404 al subir por PAR | Falta la barra final en `OCI_PAR_URL`, o la PAR es de solo lectura |
| `columnas_perfil … no coinciden` | El artefacto se entrenó con otra versión de `features.py`. Reentrena el notebook. |
| El historial no aparece en el bucket | `OCI_HISTORIAL=false`, o la PAR no tiene permiso de escritura |
