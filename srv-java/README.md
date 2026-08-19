# FinanceAI · backend (finance-ai-api)

Orquestador Spring Boot. Valida la entrada, coordina las dos llamadas al ml-service, aplica
las reglas de negocio y archiva el resultado en OCI Object Storage.

Es la **única puerta de entrada**: el frontend habla solo con este servicio y el ml-service
no se expone al navegador.

## Correr

```bat
mvnw.cmd spring-boot:run   :: http://localhost:8080/swagger-ui.html
mvnw.cmd test              :: 49 tests
```

En Linux/macOS: `./mvnw spring-boot:run`.

Requisitos: **JDK 25**. Maven no hace falta instalarlo: `mvnw` descarga la versión correcta
(3.9.9) a `~/.m2/wrapper` la primera vez. Si ya tienes Maven, `mvn` funciona igual.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/analisis-financiero` | Clasificación + perfil + recomendaciones |
| POST | `/api/v1/clasificar-transacciones` | Solo categorización |
| GET | `/api/v1/health` | Liveness (sin llamadas de red) |
| GET | `/api/v1/version` | Versión del MVP |
| GET | `/api/v1/ml-status` | Estado del modelo y del almacenamiento |

Referencia completa: [docs/API-ENDPOINTS.md](docs/API-ENDPOINTS.md)
Ejemplos ejecutados: [../docs/EJEMPLOS.md](../docs/EJEMPLOS.md)

## Flujo de un análisis

```
FinancialController
  └─ FinancialAnalysisService
       ├─ ClassificationService  → POST /clasificar   (solo transacciones)
       ├─ [agregación por categoría, aquí en Java]
       ├─ ProfileService         → POST /perfil       (solo agregados)
       ├─ RecommendationService  (reglas de negocio, siempre local)
       └─ OCIStorageService      (archivado asíncrono, best-effort)
```

Dos llamadas HTTP por análisis, siempre por lote. Con 200 transacciones, una llamada por
transacción serían 200 viajes de ida y vuelta.

## Antes de tocar el código

- `PythonModelClient` no lanza. Ante un fallo de red o un error del ml-service devuelve
  `Optional.empty()` y quien llama decide cómo degradar, para que una caída del servicio de
  modelos no acabe en un 5xx.
- Los timeouts son explícitos (1 s de conexión, 2 s de lectura). Sin ellos, un ml-service
  colgado bloquea el hilo de Tomcat y con él la API.
- El monto sale de la petición, no del eco del modelo. Del modelo solo se toman categoría y
  confianza. `ClassificationServiceTest` lo fija.
- La respuesta del modelo se verifica antes de usarla: una categoría por transacción enviada
  y en el mismo orden, o se cae al respaldo. Un perfil fuera de las tres etiquetas canónicas
  también se descarta.
- Las recomendaciones viven en Java, no en el modelo, porque son reglas de negocio que hay
  que poder explicar y cambiar sin reentrenar. Los umbrales de comparación
  (`PATRON_SALUDABLE`) sí vienen del notebook.
- El archivado en OCI no bloquea ni rompe: va en un pool de un solo hilo, acotado para que
  una caída de Object Storage no acumule tareas hasta agotar memoria.

## Configuración

```properties
ml.service.url=${ML_SERVICE_URL:http://localhost:8000}
ml.service.enabled=${ML_SERVICE_ENABLED:true}       # false fuerza el modo degradado
ml.service.connect-timeout=1s
ml.service.read-timeout=2s
ml.service.confianza-minima=0.5                     # por debajo, la categoría pasa a "otras"

oci.par-url=${OCI_PAR_URL:}                         # vacío = no se archiva nada
oci.bucket=${OCI_BUCKET:finance-ai-models}
oci.historial-habilitado=${OCI_HISTORIAL:true}

app.cors.allowed-origins=${CORS_ALLOWED_ORIGINS:...}
```

## Estructura

```
config/       propiedades y beans (RestClient con timeouts, CORS, OpenAPI)
controller/   FinancialController — validación y traducción HTTP
dto/          contratos de entrada y salida, con Bean Validation
exception/    GlobalExceptionHandler — 400 estructurado por campo
integration/  PythonModelClient, FallbackClassifier, OCIStorageService
model/        FinancialCategory, FinancialProfile
service/      lógica de orquestación y reglas de negocio
```
