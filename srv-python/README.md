# FinanceAI · ml-service — v1.0

Servicio de inferencia. Carga los modelos entrenados y responde dos preguntas: en qué
categoría cae una transacción, y qué perfil financiero describe a un usuario.

## Correr

```bash
python -m venv .venv
.venv/Scripts/activate                        # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt           # pytest + httpx, solo para pruebas
uvicorn app.main:app --reload --port 8000     # docs: http://localhost:8000/docs
./curl.sh                                     # ejemplos contra el servicio local
pytest -q                                     # 50 pruebas
```

## De dónde salen los modelos

`app/modelos.py` los resuelve en este orden, y **nunca falla el arranque**:

| Orden | Origen | Cuándo |
|---|---|---|
| 1 | **OCI Object Storage** | Despliegue. Se descargan al arrancar; la imagen no los lleva dentro |
| 2 | **Disco local** (`ciencia-datos/artefactos/`) | Desarrollo, o si OCI no responde |
| 3 | **Reglas por palabras clave** | Sin artefactos. Capacidad reducida, declarada en `/modelo/info` |

Un ml-service que no arranca deja al backend en modo degradado permanente. Arrancar con
capacidades reducidas y declararlo es mejor.

Comprobar qué está sirviendo:

```bash
curl -s localhost:8000/modelo/info | jq '{origen, version, clasificador_cargado, errores}'
```

Configuración de OCI: [docs/OCI.md](../docs/OCI.md).

## Endpoints

| Método | Ruta | Entrada | Salida |
|---|---|---|---|
| POST | `/clasificar` | solo `transacciones` | categoría + confianza + `resumen_gastos` |
| POST | `/perfil` | solo agregados | perfil + probabilidad + `factores` |
| GET | `/health` | — | liveness (no toca los modelos) |
| GET | `/modelo/info` | — | versión, origen, métricas, estado de OCI |

Categorías: `alimentacion · transporte · salud · vivienda · educacion · ocio · servicios · deudas · otras`
Perfiles: `Saludable · En observación · En riesgo`

## Módulos compartidos con el notebook

`features.py` y `oci_storage.py` viven en `ciencia-datos/` y no se duplican aquí. Son las
mismas funciones que se usaron al entrenar.

Si el notebook normalizara el texto de una forma y este servicio de otra, el modelo vería en
producción vectores distintos a los del entrenamiento. Eso no lo detecta ninguna métrica
offline: el modelo simplemente acierta menos, sin error ni aviso.

Por eso el `Dockerfile` construye desde la raíz del repositorio y copia esos dos archivos
dentro de `app/ciencia_datos/`:

```bash
docker build -f srv-python/Dockerfile .
```

Además, `metadatos.json` guarda el orden exacto de `COLUMNAS_PERFIL` y el servicio lo valida
al cargar: si no coincide con `features.py`, se niega a usar el artefacto en lugar de servir
predicciones sobre un vector desalineado.

## El umbral de confianza

Por debajo de `umbral_confianza` (0.5), la categoría se degrada a `otras`... pero antes se
consulta el clasificador por palabras clave de `reglas.py`. Si esa regla reconoce el
comercio, gana ella.

El notebook mide que, ante comercios nunca vistos, la accuracy del modelo cae de 0.9999 a
0.41. Las palabras clave cubren los comercios frecuentes con certeza, así que sirven de red
de seguridad y no solo de sustituto cuando el modelo está caído.

El campo `origen` de cada transacción clasificada dice cuál de los dos respondió.

> Si agregas palabras a `KEYWORDS` en `app/reglas.py`, agrégalas también en
> `srv-java/.../integration/FallbackClassifier.java`, o el modo degradado del backend dará
> un resultado distinto al de este servicio.

## Conexión con el backend Java

`PythonModelClient` llama **por lote**: una petición a `/clasificar` y una a `/perfil` por
análisis, no una por transacción.

```properties
ml.service.url=${ML_SERVICE_URL:http://localhost:8000}
ml.service.enabled=${ML_SERVICE_ENABLED:true}
ml.service.connect-timeout=1s
ml.service.read-timeout=2s
ml.service.confianza-minima=0.5
```

Si este servicio no responde, Java **no devuelve 5xx**: cae a sus propias reglas y marca
`modo_degradado: true`. Diagnóstico: `GET http://localhost:8080/api/v1/ml-status`.

## Partición de la información

`/clasificar` no recibe ingreso, deuda ni identidad. `/perfil` no recibe las descripciones.
Ningún componente de inferencia ve al usuario completo; solo el orquestador Java.
