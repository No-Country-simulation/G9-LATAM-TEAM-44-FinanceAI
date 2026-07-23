# FinanceAI · ml-service (contrato ejecutable) — v0.1

Este servicio **define el contrato** entre `finance-ai-api` (Java, 4 capas) y el
servicio de AI, y **funciona hoy** con reglas stub para que el backend integre sin
esperar a los modelos. Los TODO(DS)/TODO(ML) marcan dónde entran los artefactos reales.

## Correr
```bash
python -m venv venv # crea tu ambiente de python.
venv/Scripts/activate # activa tu ambiente.
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000   # docs interactivas: http://localhost:8000/docs
./curl.sh                                    # ejemplos del contrato
pip install pytest httpx && pytest -q        # pruebas del contrato
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

## Conectar el backend Java (reemplazo de PythonModelClient)
`application.properties`:
```properties
ml.service.url=http://localhost:8000
```
Cliente por lotes (una llamada por request, no por transacción):
```java
RestClient rc = RestClient.builder().baseUrl(mlServiceUrl).build();
ClasificarResponse out = rc.post().uri("/clasificar")
    .body(new ClasificarRequest(transacciones))
    .retrieve().body(ClasificarResponse.class);
```
Timeout 2 s + si el servicio no responde, conservar las reglas actuales de
`PythonModelClient` como fallback y marcar `modo_degradado` (UC1 · alternativo A2).

## Partición de la información (necesidad de saber)
`/clasificar` nunca recibe ingreso, deuda ni identidad; `/perfil` nunca recibe las
descripciones crudas. El orquestador Java es el único que ve el cuadro completo.
