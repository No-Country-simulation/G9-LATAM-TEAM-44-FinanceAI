# FinanceAI — G9 LATAM Equipo 44

Hackathon ONE · Oracle Next Education.

Categoriza los gastos de un extracto bancario en nueve categorías, diagnostica la salud
financiera del usuario y devuelve recomendaciones.

```
Navegador  ->  web (:8081)  ->  srv-java (:8080)  ->  srv-python (:8000)  ->  OCI Object Storage
               frontend         orquestador           inferencia              modelos + historial
               + proxy          reglas de negocio     clasificador + perfil
```

El ml-service no se expone al navegador.

---

## Arrancar

Requisitos: JDK 25 y Python 3.10+. Maven no hace falta, el proyecto trae `mvnw` y se descarga
la versión correcta la primera vez.

### Un comando

```bash
# solo la primera vez
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r srv-python\requirements.txt

iniciar.cmd          # Windows (o doble clic)
./iniciar.sh         # Linux / macOS
```

| Servicio | URL |
|---|---|
| Frontend | http://localhost:8081 |
| API · Swagger | http://localhost:8080/swagger-ui.html |
| ml-service · docs | http://localhost:8000/docs |
| Estado del modelo | http://localhost:8080/api/v1/ml-status |

### Tres terminales

```bat
:: 1 - inferencia
cd srv-python
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

:: 2 - backend
cd srv-java
mvnw.cmd spring-boot:run

:: 3 - frontend
cd web
..\.venv\Scripts\python.exe -m http.server 8081
```

En Linux/macOS, las mismas rutas con `/`, `.venv/bin/python` y `./mvnw`.

### Docker

```bash
docker compose up -d --build
```

Compose levanta tres servicios: `web`, `api` y `ml-service`. **n8n no está incluido**, ver
la sección siguiente.

El ml-service no publica puerto: solo se llega a él desde la red interna del stack.

Para desplegar en un servidor con Portainer, ver [docs/DESPLIEGUE-OCI.md](docs/DESPLIEGUE-OCI.md).

Aviso: las imágenes nunca se han construido en la máquina de desarrollo, que no tenía Docker.
La ruta de las tres terminales sí está comprobada de punta a punta.

El frontend detecta solo a qué backend hablar: primero prueba el mismo origen (detrás del
proxy de nginx) y si no responde, `http://localhost:8080`.

### El chat y n8n

El chat usa una instancia de **n8n externa al stack**, no una que levante este compose. Es
una decisión de despliegue: el servidor ya tenía n8n corriendo, y arrancar un segundo choca
con el puerto 5678 y consume memoria que no sobra.

Cómo encaja:

1. El frontend llama a `/n8n/webhook/chat-support`, del mismo origen.
2. nginx reenvía esa ruta al contenedor de n8n. El nombre está en `web/nginx.conf`
   (`n8n-n8n-1` por defecto); si el tuyo se llama de otra forma, cámbialo ahí.
3. Para que se vean entre sí, el servicio `web` se conecta a la red donde vive n8n. Se
   configura con la variable `RED_N8N` (por defecto `npm_network`).

El workflow está en `n8n-orquestacion/`, pero **es una copia de referencia, no la fuente**:
hay que importarlo a mano en n8n. Editarlo en el repositorio no cambia nada en producción.

Al importarlo hacen falta dos cosas que no viajan en el JSON:

- La **credencial de Gemini** en el nodo `Google Gemini Chat Model`.
- **Publicar** el workflow, o el webhook de producción devuelve 404.

nginx resuelve el nombre de n8n en cada petición, no al arrancar. Así, si n8n no está
disponible, solo falla `/n8n/` con un 502 y el frontend sigue funcionando.

---

## Qué hay dentro

| Carpeta | Contenido |
|---|---|
| `ciencia-datos/` | Notebook de entrenamiento, generador de datos, `features.py`, cliente de OCI |
| `srv-python/` | ml-service FastAPI: carga los modelos e infiere |
| `srv-java/` | Orquestador Spring Boot: valida, orquesta, aplica reglas de negocio |
| `web/` | Frontend: análisis, clasificador y evolución |
| `docs/` | Ejemplos, integración con OCI y notas de arquitectura |
| `postman/` | Colección de pruebas de ambos servicios |

### Frontend

Tres pestañas: análisis (formulario, perfil con medidor de confianza, dona de gastos,
recomendaciones y factores), clasificador (pegas descripciones y ves cómo se categorizan con
su confianza) y evolución (histórico local con línea de tendencia).

Cada categoría de la dona se abre y muestra las transacciones que la componen, con su
confianza. Las que el modelo no dio por buenas salen marcadas, junto a la categoría que
quedó segunda, y la cabecera lleva un contador de cuántas conviene revisar. Antes el
agregado no dejaba comprobar dónde había acabado cada movimiento.

Trae tres casos de ejemplo, importación de CSV, exportación del informe a JSON, impresión a
PDF, tema claro/oscuro y aviso cuando la respuesta viene en modo degradado.

Son tres archivos que el navegador abre directamente, sin framework ni empaquetador. Los
iconos son un sprite SVG en línea y los gráficos están hechos a mano, así que la página no
hace ninguna petición externa.

Dos detalles: la paleta de categorías vive en variables CSS y el SVG las referencia sin
resolver, de modo que los gráficos ya pintados siguen el cambio de tema; y
`prefers-reduced-motion` desactiva las animaciones, incluidas las de los gráficos.

### Documentación

- [Ejemplos de uso](docs/EJEMPLOS.md) — seis casos ejecutados contra la API
- [Referencia de endpoints](srv-java/docs/API-ENDPOINTS.md)
- [Integración con OCI](docs/OCI.md) — bucket, credenciales y modelos
- [Despliegue en OCI Compute](docs/DESPLIEGUE-OCI.md) — Portainer, puertos y dominio
- [Arquitectura](docs/ARQUITECTURA.md) — decisiones y sus contrapartidas
- [Notebook](ciencia-datos/notebook.ipynb) — EDA, entrenamiento, métricas y serialización

---

## Los modelos

Dos modelos, entrenados sobre un dataset sintético de 400 usuarios × 6 meses (~64.700
transacciones) con semilla fija.

| Modelo | Algoritmo | Métrica |
|---|---|---|
| Clasificador de gastos | TF-IDF (palabras + caracteres) → `LinearSVC` calibrado | accuracy 0.9999 · f1-macro 0.9999 |
| Perfil financiero | `StandardScaler` → Regresión logística | accuracy 0.849 · f1-macro 0.836 |

Sobre el 0.9999: en el dataset cada comercio pertenece a una sola categoría, así que
memorizar el nombre basta y esa cifra no dice gran cosa. La medida útil es la otra: evaluando
contra comercios que el modelo nunca vio, la accuracy baja a 0.47.

De ahí salen tres decisiones de diseño:

1. Umbral de confianza 0.5 sobre `predict_proba`. Por debajo, la API devuelve `otras`. Ese
   número no es una probabilidad real de acertar (el modelo no está calibrado sobre comercios
   no vistos: ECE 0.3890 y Brier score 0.1083 evaluando out-of-fold, ver
   `ciencia-datos/experimentos/calibracion.json`); se usa solo como score para decidir cuándo
   abstenerse. En un informe financiero un gasto sin clasificar molesta menos que uno mal
   atribuido.
2. Clasificador de respaldo por palabras clave, que cubre los comercios frecuentes y entra
   también cuando el modelo duda.
3. El catálogo de comercios hay que alimentarlo. La mejora viene de reentrenar con comercios
   nuevos, no de cambiar de algoritmo.

El modelo de perfil se valida con `StratifiedGroupKFold` agrupada por usuario. Sin agrupar,
los seis meses de una misma persona se reparten entre train y test y la métrica premia
reconocer al usuario en lugar de entender su comportamiento.

Su vector de atributos son 18 columnas, todas adimensionales: ratios, porcentajes y conteos.
Ningún monto. La aplicación acepta varias monedas y no las convierte, así que un monto crudo
en el vector hacía que el diagnóstico dependiera de la unidad en que el usuario escribiera
las cifras: el mismo caso salía `Saludable` en dólares y `En observación` en pesos. Sobre
ratios el factor de conversión se cancela. Ver [ARQUITECTURA.md](docs/ARQUITECTURA.md).

### Reentrenar

```bash
pip install -r ciencia-datos/requirements.txt
python ciencia-datos/scripts/generador_usuarios.py --usuarios 400 --semilla 42
jupyter notebook ciencia-datos/notebook.ipynb    # o jupyter nbconvert --execute --inplace
```

Los artefactos quedan en `ciencia-datos/artefactos/` y, con credenciales, se publican en OCI
Object Storage.

---

## OCI

| Servicio | Uso |
|---|---|
| Object Storage | Guarda los modelos (el notebook los sube, el ml-service los descarga al arrancar) y archiva cada análisis |
| Compute | Aloja los tres contenedores con `docker compose`. Ver [DESPLIEGUE-OCI.md](docs/DESPLIEGUE-OCI.md) |

La imagen del ml-service no lleva los modelos dentro, los baja al iniciar. Publicar un modelo
reentrenado es subir un objeto y reiniciar el contenedor.

Configuración en [docs/OCI.md](docs/OCI.md). Sin credenciales el sistema funciona con los
artefactos locales, y `/modelo/info` indica de dónde salió el modelo que está sirviendo:
`oci`, `local` o `reglas`.

---

## Modo degradado

Si `srv-python` no responde, la API no devuelve 5xx. Usa el clasificador por palabras clave y
los umbrales locales, responde con la misma estructura y marca `modo_degradado: true`. El
frontend muestra un aviso de resultado aproximado.

Timeouts: 1 s de conexión, 2 s de lectura. Para forzarlo sin apagar nada:

```properties
ml.service.enabled=false        # o ML_SERVICE_ENABLED=false
```

---

## Pruebas

```bash
cd srv-java   && mvnw.cmd test   # 67 tests
cd srv-python && pytest -q       # 84 tests

python docs/ejemplos.py          # prueba end-to-end contra la API levantada
newman run postman/FinanceAI.postman_collection.json
```

---

## Tratamiento de los datos

El flujo parte la información para que ningún componente de inferencia vea al usuario
completo:

1. `POST /clasificar` recibe solo transacciones. No ve ingreso ni deuda.
2. El backend agrega los montos por categoría.
3. `POST /perfil` recibe solo agregados. No ve las descripciones.
4. Las recomendaciones se generan en Java, con reglas auditables.

Solo el backend Java tiene la foto completa. El historial que se archiva en Object Storage
guarda perfil, agregados e indicadores, no las descripciones de las transacciones.

---

## Limitaciones

- Los datos son simulados. Las métricas miden si el modelo aprende una estructura conocida,
  no su desempeño con extractos reales.
- El modelo de perfil hereda los pesos de la regla de simulación. Con datos reales habría que
  recalibrarlo contra una definición de salud financiera validada por alguien del dominio.
- No hay componente temporal. Cada periodo se evalúa por separado; el frontend muestra la
  evolución pero el modelo no la usa para predecir.
- El historial vive en Object Storage, no en una base de datos. Sirve para archivar y
  analizar en lote, no para consultas por usuario en tiempo real.
