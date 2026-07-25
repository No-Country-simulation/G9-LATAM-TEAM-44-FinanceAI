# FinanceAI · ml-service (contrato ejecutable) — v0.1

Este servicio **define el contrato** entre `finance-ai-api` (Java, 4 capas) y el
servicio de AI, y **funciona hoy** con reglas stub para que el backend integre sin
esperar a los modelos. Los TODO(DS)/TODO(ML) marcan dónde entran los artefactos reales.

## Correr
```bash
python -m venv .venv                          # crea tu ambiente de python
.venv/Scripts/activate                        # activa tu ambiente (Windows)
pip install -r requirements.txt               # dependencias de ejecucion
pip install -r requirements-dev.txt           # pytest + httpx (solo para pruebas)
uvicorn app.main:app --reload --port 8000     # docs interactivas: http://localhost:8000/docs
./curl.sh                                     # ejemplos del contrato
pytest -q                                     # pruebas del contrato
```

## El contrato (resumen)
- `POST /clasificar`  — entra SOLO `{transacciones:[{descripcion, valor}]}`;
  sale `{transacciones_clasificadas:[{descripcion, valor, categoria, confianza}]}`.
- `POST /perfil`      — entran SOLO agregados `{ingreso_mensual, nivel_endeudamiento,
  frecuencia_ahorro, resumen_gastos}`; sale `{perfil_financiero, probabilidad, factores[]}`.
- `GET /health` · `GET /modelo/info`.

Categorías canónicas (= enum `FinancialCategory` del backend, en minúscula):
`alimentacion, transporte, salud, vivienda, educacion, ocio, servicios, otras`.
Perfiles: `Saludable · En observación · En riesgo`. Los umbrales del stub replican
`FinancialAnalysisService` (deuda≥50 o gasto/ingreso≥1 → riesgo; ≥30 o ≥0.8 → observación).

## Conexión con el backend Java — YA IMPLEMENTADA

`PythonModelClient` (Java) llama a este servicio por HTTP, **por lote**: una
petición a `/clasificar` y una a `/perfil` por análisis, no una por transacción.

Configuración en `srv-java/src/main/resources/application.properties`:
```properties
ml.service.url=${ML_SERVICE_URL:http://localhost:8000}
ml.service.enabled=${ML_SERVICE_ENABLED:true}
ml.service.connect-timeout=1s
ml.service.read-timeout=2s
ml.service.confianza-minima=0.5
```

Comportamiento ante fallos (UC1 · alternativo A2): si este servicio no responde,
Java **no devuelve 5xx**. Cae a las reglas por palabra clave de
`FallbackClassifier` (espejo de `KEYWORDS` de este archivo) y marca
`modo_degradado: true` en la respuesta.

> Si agregas palabras a `KEYWORDS`, agrégalas también en
> `srv-java/.../integration/FallbackClassifier.java` para que el modo degradado
> siga dando resultados equivalentes.

Diagnóstico rápido: `GET http://localhost:8080/api/v1/ml-status`

## Partición de la información (necesidad de saber)
`/clasificar` nunca recibe ingreso, deuda ni identidad; `/perfil` nunca recibe las
descripciones crudas. El orquestador Java es el único que ve el cuadro completo.
