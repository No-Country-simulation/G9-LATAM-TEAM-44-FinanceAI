# FinanceAI — G9 LATAM Team 44

API que integra un modelo de Machine Learning (Python) en un backend Java Spring
Boot. Automatiza la categorización de gastos y el diagnóstico de salud financiera.

## Arquitectura

```
Frontend  ──►  srv-java (:8080)  ──►  srv-python (:8000)
               orquestador            servicio de AI
```

El orquestador Java hace **dos llamadas por análisis**, con partición
"necesidad de saber":

1. `POST /clasificar` — recibe **solo transacciones**. Nunca ve el ingreso ni la deuda.
2. Java agrega los montos por categoría.
3. `POST /perfil` — recibe **solo agregados**. Nunca ve las descripciones crudas.
4. Java genera las recomendaciones.

Solo el backend Java ve el cuadro completo.

**El frontend habla únicamente con `:8080`.** El ml-service no se expone al navegador.

## Levantar todo

### Con Docker (recomendado)

```bash
docker compose up --build
```

### A mano

```bash
# Terminal 1 — servicio de AI
cd srv-python
python -m venv .venv && .venv/Scripts/activate      # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 — backend
cd srv-java
mvn spring-boot:run
```

| Servicio | URL |
|---|---|
| API (Swagger) | http://localhost:8080/swagger-ui.html |
| ml-service (docs) | http://localhost:8000/docs |
| Estado de la integración | http://localhost:8080/api/v1/ml-status |

Requisitos: **JDK 17+**, **Python 3.10+**, Maven 3.9+.

## Desarrollar el frontend sin levantar Python

El backend funciona igual con el ml-service apagado: cae a reglas locales y
marca `modo_degradado: true`. Para forzarlo explícitamente:

```properties
ml.service.enabled=false
```

o `ML_SERVICE_ENABLED=false` como variable de entorno.

## Modo degradado

Si srv-python no responde, la API **no devuelve 5xx**: usa el clasificador de
respaldo por palabras clave y responde con la misma estructura, marcando
`modo_degradado: true`. El frontend debería mostrar un aviso de "resultado
aproximado" cuando ese campo venga en `true`.

Timeouts: 1 s de conexión, 2 s de lectura.

## Pruebas

```bash
cd srv-java   && mvn test        # 20 tests
cd srv-python && pytest -q       # 3 tests

# Colección Postman (requiere newman)
newman run postman/FinanceAI.postman_collection.json
```

## Estructura

| Carpeta | Contenido |
|---|---|
| `srv-java/` | Orquestador Spring Boot (controller · service · integration · dto) |
| `srv-python/` | Servicio de AI FastAPI + scripts de generación y limpieza de datos |
| `ciencia-datos/` | Notebook de entrenamiento y `features.py` |
| `postman/` | Colección de pruebas de ambos servicios |

Documentación de la API: [srv-java/docs/API-ENDPOINTS.md](srv-java/docs/API-ENDPOINTS.md)

## Pendiente

- Entrenar y serializar los modelos (`ciencia-datos/notebook.ipynb` está vacío).
- Cargar los modelos reales en `srv-python` (ver los `TODO(ML)` en `app/main.py`).
- Subida real a OCI Object Storage (`OCIStorageService` hoy devuelve una ruta fija).
- Frontend.
- Persistencia e historial de análisis (hoy no hay base de datos).
