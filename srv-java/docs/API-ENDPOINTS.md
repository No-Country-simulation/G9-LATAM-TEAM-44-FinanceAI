# API FinanceAI · Referencia de endpoints

Base URL local: `http://localhost:8080`
Swagger UI: `/swagger-ui.html` · OpenAPI JSON: `/api-docs`

Todo el JSON va en **snake_case** (`spring.jackson.property-naming-strategy=SNAKE_CASE`).

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/v1/analisis-financiero` | Análisis completo: clasificación + perfil + recomendaciones |
| POST | `/api/v1/clasificar-transacciones` | Solo categorización de transacciones |
| GET | `/api/v1/health` | Liveness (no consulta el ml-service) |
| GET | `/api/v1/version` | Versión del MVP |
| GET | `/api/v1/ml-status` | Estado del modelo y del almacenamiento |
| GET | `/api/v1/metricas-modelo` | Resumen de métricas de evaluación del modelo (proxy a srv-python) |

Tres ejemplos completos de uso: [docs/EJEMPLOS.md](../../docs/EJEMPLOS.md)

---

## POST /api/v1/analisis-financiero

### Petición

```json
{
  "ingreso_mensual": 4500,
  "nivel_endeudamiento": 12,
  "frecuencia_ahorro": "Alta",
  "transacciones": [
    { "descripcion": "Supermercado Exito", "valor": 420 },
    { "descripcion": "Gasolinera Terpel", "valor": 180 },
    { "descripcion": "Netflix Streaming", "valor": 40 },
    { "descripcion": "Arriendo Apartamento", "valor": 900 }
  ]
}
```

Restricciones. Están alineadas con el contrato de `srv-python`: lo que allí sería un 422
opaco, aquí se rechaza antes con un 400 y un mensaje por campo.

| Campo | Regla |
|---|---|
| `ingreso_mensual` | requerido, > 0 |
| `nivel_endeudamiento` | requerido, entero entre 0 y 100 |
| `frecuencia_ahorro` | requerido: `Alta`, `Media`, `Baja` o `Nula` (indiferente a mayúsculas) |
| `transacciones` | requerido, entre 1 y 5000 elementos |
| `transacciones[].descripcion` | requerido, 1 a 200 caracteres |
| `transacciones[].valor` | requerido, > 0 |

### Respuesta 200

```json
{
  "perfil_financiero": "Saludable",
  "probabilidad": 1.0,
  "resumen_gastos": {
    "alimentacion": 420.0,
    "transporte": 180.0,
    "ocio": 40.0,
    "vivienda": 900.0
  },
  "recomendaciones": [
    "Tu gasto en transporte representa el 12% del total, 1.9 veces el patrón de un perfil saludable. Es la palanca más rápida para liberar margen."
  ],
  "factores": [
    { "nombre": "ratio_endeudamiento", "valor": 0.12,   "impacto": "baja_riesgo" },
    { "nombre": "ahorro_ordinal",      "valor": 3.0,    "impacto": "baja_riesgo" },
    { "nombre": "capacidad_ahorro",    "valor": 0.6578, "impacto": "baja_riesgo" }
  ],
  "transacciones_clasificadas": [
    { "descripcion": "Supermercado Exito", "valor": 420.0, "categoria": "alimentacion", "confianza": 0.9993, "estado_confianza": "aceptado", "top3": [ ... ] },
    { "descripcion": "Arriendo Apartamento", "valor": 900.0, "categoria": "vivienda", "confianza": 0.9995, "estado_confianza": "aceptado", "top3": [ ... ] }
  ],
  "modo_degradado": false
}
```

| Campo | Notas |
|---|---|
| `perfil_financiero` | `Saludable`, `En observación` o `En riesgo` (con tilde) |
| `probabilidad` | 0..1, confianza del modelo en la clase asignada |
| `resumen_gastos` | Solo las categorías **con gasto**. La ausencia de una clave equivale a 0 |
| `recomendaciones` | Entre 1 y 4, ordenadas por impacto. Nunca vacío |
| `factores` | Los 3 atributos que más pesaron. Ver la nota de abajo |
| `transacciones_clasificadas` | Una entrada por transacción recibida, en el mismo orden. Misma forma que en `/clasificar-transacciones` |
| `modo_degradado` | `true` = calculado con reglas locales, no con el modelo |

`transacciones_clasificadas` sale de la misma llamada al modelo que `resumen_gastos`, así que
no cuesta una clasificación extra. Está para poder abrir cada porción del gráfico y ver de
qué transacciones se compone: con solo el agregado no había forma de comprobar dónde había
ido a parar cada movimiento, ni de detectar los que el modelo no supo asignar.

Ese detalle **no se archiva** en Object Storage. El registro del historial guarda perfil,
agregados e indicadores; las descripciones se quedan en la respuesta.

### Cómo leer `factores`

`impacto` indica hacia dónde empuja el atributo en comparación con el usuario promedio de la
población de entrenamiento, no en términos absolutos.

Por eso un `ratio_endeudamiento` de 0.35 puede aparecer como `baja_riesgo`: 35% está por
debajo de la media del conjunto de datos. Sale de la regresión logística, donde la
contribución es *coeficiente × valor estandarizado*, y estandarizar centra cada atributo en
su media.

Un cliente no debería presentarlo como un juicio absoluto. La lectura correcta es "frente a
un usuario promedio, esto te acerca o te aleja del riesgo".

### `modo_degradado`

- `false` → el resultado viene de los modelos entrenados en `srv-python`.
- `true` → `srv-python` no respondió y el análisis se calculó con las reglas de respaldo
  locales. La respuesta es válida y tiene la misma forma; el cliente debería mostrar un aviso
  de resultado aproximado.

No se devuelve un 5xx porque el ml-service esté caído.

### Respuesta 400

```json
{
  "mensaje": "Error de validación en los campos enviados",
  "codigo_estado": 400,
  "timestamp": "2026-08-17T18:01:16.849",
  "detalles": {
    "ingresoMensual": "El ingreso mensual debe ser mayor a 0",
    "nivelEndeudamiento": "El nivel de endeudamiento es un porcentaje: maximo 100",
    "frecuenciaAhorro": "La frecuencia de ahorro debe ser Alta, Media, Baja o Nula",
    "transacciones": "Se requiere entre 1 y 5000 transacciones"
  }
}
```

Las claves de `detalles` son los nombres de los campos **Java** (camelCase), no los del JSON.
Es el comportamiento por defecto de Bean Validation.

---

## POST /api/v1/clasificar-transacciones

Categorización aislada. No pide ingreso ni endeudamiento porque no los necesita: clasificar
una transacción no requiere conocer la situación financiera de quien la hizo.

### Petición

```json
{
  "transacciones": [
    { "descripcion": "Supermercado Exito", "valor": 420 },
    { "descripcion": "TRF/POS Gasolinera Terpel REF88213", "valor": 300 },
    { "descripcion": "Netflix Streaming", "valor": 40 },
    { "descripcion": "### farmacia cruz verde", "valor": 85 },
    { "descripcion": "zxqw plfj mmnb", "valor": 25 }
  ]
}
```

### Respuesta 200

```json
{
  "transacciones_clasificadas": [
    { "descripcion": "Supermercado Exito",                 "valor": 420.0, "categoria": "alimentacion", "confianza": 0.9993, "estado_confianza": "aceptado",
      "top3": [ { "categoria": "alimentacion", "confianza": 0.9993 }, { "categoria": "otras", "confianza": 0.0004 }, { "categoria": "ocio", "confianza": 0.0002 } ] },
    { "descripcion": "TRF/POS Gasolinera Terpel REF88213",  "valor": 300.0, "categoria": "transporte",   "confianza": 0.9994, "estado_confianza": "aceptado",
      "top3": [ { "categoria": "transporte", "confianza": 0.9994 } ] },
    { "descripcion": "Netflix Streaming",                   "valor": 40.0,  "categoria": "ocio",         "confianza": 0.9995, "estado_confianza": "aceptado",
      "top3": [ { "categoria": "ocio", "confianza": 0.9995 } ] },
    { "descripcion": "### farmacia cruz verde",             "valor": 85.0,  "categoria": "salud",        "confianza": 0.9996, "estado_confianza": "aceptado",
      "top3": [ { "categoria": "salud", "confianza": 0.9996 } ] },
    { "descripcion": "zxqw plfj mmnb",                      "valor": 25.0,  "categoria": "otras",        "confianza": 0.3573, "estado_confianza": "otras",
      "top3": [ { "categoria": "otras", "confianza": 0.3573 }, { "categoria": "vivienda", "confianza": 0.1204 }, { "categoria": "servicios", "confianza": 0.0891 } ] }
  ],
  "resumen_gastos": {
    "alimentacion": 420.0, "transporte": 300.0, "ocio": 40.0, "salud": 85.0, "otras": 25.0
  },
  "total_gastos": 870.0,
  "modo_degradado": false
}
```

En la última, `zxqw plfj mmnb` no se parece a nada conocido: la confianza cae a 0.36 y por
debajo del umbral de 0.5 la categoría pasa a `otras`. En un informe financiero un gasto sin
clasificar molesta menos que uno mal atribuido; el notebook (sección 10.2) mide cuánto cuesta
y cuánto aporta ese umbral.

`descripcion` y `valor` se devuelven tal cual llegaron. El monto sale de la petición, no del
eco del modelo.

#### `estado_confianza` (Fase 12 — estrategia de abstención)

Adicional a `categoria` y `confianza`, cada transacción trae un estado explícito que no
reemplaza nada de lo anterior: `categoria` sigue siendo la que ya se devolvía (incluida su
degradación a `otras` por debajo de `umbral_confianza`) y `confianza` no cambia de escala.

Los cortes salen de la tabla real `coverage_vs_accuracy` de
`ciencia-datos/experimentos/calibracion.json` (Fase 5 — calibración y umbral de confianza),
calculada sobre 58 894 filas out-of-distribution con `accuracy_global_ood = 0.4264271402859374`:

| umbral | coverage | filas_aceptadas | accuracy_aceptadas |
|---|---|---|---|
| 0.5 | 0.8181987978401875 | 48187 | 0.45240417540000416 |
| 0.6 | 0.6731755357082215 | 39646 | 0.49301316652373506 |
| 0.7 | 0.5888375725880395 | 34679 | 0.5015715562732489 |
| **0.8** | **0.5426529018236154** | **31959** | **0.5223254795206358** |
| 0.9 | 0.4636465514313852 | 27306 | 0.5669816157621036 |

Con esa tabla:

- **`aceptado`**: `confianza >= umbral_confianza_alta` (0.8 por defecto). En ese punto la
  accuracy de lo aceptado es 0.5223254795206358, +9.59 puntos absolutos sobre el
  0.4264271402859374 global (+22.5% relativo), reteniendo coverage=0.5426529018236154 (más de
  la mitad del tráfico). En 0.9 la accuracy sube a 0.5669816157621036 pero el coverage cae a
  0.4636465514313852: 0.8 es el mejor punto que sigue aceptando más de la mitad de las
  transacciones sin marcarlas para revisión.
- **`requiere_revision`**: `umbral_confianza <= confianza < umbral_confianza_alta` (0.5–0.8 por
  defecto). En el propio `umbral_confianza` (0.5, el mismo que ya usa el fallback a `otras`,
  sin cambios) la accuracy_aceptadas es 0.45240417540000416: mejor que el azar entre 8
  categorías, pero no lo bastante fiable para aceptar sin marcar. La predicción se devuelve
  igual (no se pierde información), solo va señalada.
- **`otras`**: `confianza < umbral_confianza`. Comportamiento sin cambios: la categoría ya se
  degradaba a `otras` en este rango; el ECE=0.3335 de la Fase 5 confirma que el modelo está mal
  calibrado en OOD, así que por debajo de este punto no se puede confiar en el número crudo de
  confianza.

`umbral_confianza_alta` (0.8) se expone en `GET /modelo/info` (srv-python) junto al ya existente
`umbral_confianza` (0.5), y en srv-java se configura con `ml.service.confianza-alta` (espejo de
`ml.service.confianza-minima`). Ver `RegistroModelos.umbral_confianza_alta` en
`srv-python/app/modelos.py` y `ClassificationService.resolverEstadoConfianza` en srv-java para
la implementación y el detalle de las cifras.

#### `top3` (Fase 16)

Adicional a `categoria`, `confianza` y `estado_confianza`, cada transacción trae hasta 3
categorías candidatas con su confianza, en orden descendente. `top3[0]` coincide siempre con
`categoria` (la decisión final, ya aplicados el umbral y las reglas de respaldo): es aditivo, no
reemplaza nada de lo anterior.

Sale de `predict_proba` del clasificador calibrado en srv-python. En modo reglas o degradado
(sin clasificador cargado, o el propio respaldo por palabras clave de srv-java) `top3` trae un
solo elemento, porque no hay una distribución de probabilidades que ofrecer más allá de la
categoría de la keyword. Ver `_top3_desde_fila` en `srv-python/app/main.py` y
`ClassificationService.top3DesdeModelo` en srv-java.

### Categorías

`alimentacion` · `transporte` · `salud` · `vivienda` · `educacion` · `ocio` · `servicios` · `deudas` · `otras`

`deudas` recoge los pagos de tarjeta de crédito y las cuotas de crédito de consumo. La cuota
de la hipoteca no: va en **vivienda**, porque quien la paga la vive como el coste de su casa.

El streaming (Netflix, Spotify, Disney+) se clasifica como **ocio**, no como servicios: es
entretenimiento aunque se cobre como suscripción. `servicios` queda para telecomunicaciones,
servicios públicos y software.

---

## GET /api/v1/ml-status

Diagnóstico de la integración. Va aparte de `/health` porque ese es liveness y no debe hacer
llamadas de red: un ml-service lento haría fallar el health check de la propia API.

```json
{
  "ml_service_url": "http://localhost:8000",
  "disponible": true,
  "modo": "modelo",
  "modelo": {
    "version": "1.0.0",
    "origen": "local",
    "clasificador_cargado": true,
    "perfil_cargado": true,
    "umbral_confianza": 0.5,
    "umbral_confianza_alta": 0.8,
    "entrenado_en": "2026-08-17T17:49:00",
    "metricas": {
      "clasificador_particion_aleatoria":  { "accuracy": 0.9999, "f1_macro": 0.9999 },
      "clasificador_comercios_no_vistos":  { "accuracy": 0.4111, "f1_macro": 0.4181 },
      "perfil_cv_agrupada":                { "accuracy": 0.8733, "f1_macro": 0.8669 }
    },
    "oci": { "via": "no_configurado", "bucket": null }
  },
  "almacenamiento": {
    "proveedor": "OCI Object Storage",
    "bucket": "finance-ai-models",
    "historial_habilitado": false,
    "modelo": "oci://finance-ai-models/clasificador_gastos.joblib"
  }
}
```

`modelo.origen`: `oci` (descargado del bucket) · `local` (artefactos en disco) · `reglas`
(sin modelo, palabras clave).

---

## GET /api/v1/metricas-modelo

Resumen condensado de las métricas de evaluación del modelo (Fase 16): baseline (partición
aleatoria vs. comercio no visto), CV agrupada por comercio, matriz de confusión OOD, métricas
por categoría, calibración y benchmark contra modelos clásicos. Es un proxy hacia
`GET /modelo/metricas` de srv-python, mismo patrón que `/ml-status` con `modelClient.infoModelo()`.
Si srv-python no responde, se devuelve `{}` (200) en vez de propagar el error.

```json
{
  "version_modelo": "1.0.0",
  "fecha": "2026-08-17T17:49:00",
  "baseline": {
    "particion_aleatoria":  { "accuracy": 0.999932, "f1_macro": 0.999929 },
    "comercio_no_visto":    { "accuracy": 0.412477, "f1_macro": 0.418918 }
  },
  "cv_agrupada": {
    "accuracy":         { "media": 0.427622, "desviacion_estandar": 0.073263 },
    "f1_macro":         { "media": 0.400717, "desviacion_estandar": 0.070891 },
    "f1_weighted":      { "media": 0.405953, "desviacion_estandar": 0.086696 },
    "balanced_accuracy":{ "media": 0.436218, "desviacion_estandar": 0.056681 }
  },
  "matriz_confusion": {
    "categorias": ["alimentacion", "transporte", "salud", "vivienda", "educacion", "ocio", "servicios", "deudas", "otras"],
    "matriz": [ [3449, 200, 4, 228, 125, 638, 179, 898], "... 7 filas mas" ],
    "accuracy_global": 0.426427
  },
  "metricas_por_categoria": [
    { "categoria": "alimentacion", "precision": 0.2668, "recall": 0.6029, "f1_score": 0.3699, "soporte": 5721, "tasa_error": 0.3971 },
    "... 7 categorias mas"
  ],
  "calibracion": {
    "coverage_vs_accuracy": [ { "umbral": 0.8, "coverage": 0.5427, "filas_aceptadas": 31959, "accuracy_aceptadas": 0.5223 }, "... otros umbrales" ],
    "expected_calibration_error": 0.3335,
    "brier_score_multiclase": 0.1152
  },
  "benchmark": [
    { "modelo": "actual (palabra+caracter TFIDF) + LinearSVC calibrado", "accuracy": "0.4276 +/- 0.0733", "f1_macro": "0.4007 +/- 0.0709", "f1_weighted": "0.4060 +/- 0.0867", "balanced_accuracy": "0.4362 +/- 0.0567" },
    "... 11 filas mas"
  ]
}
```

Generado sin conexión por `ciencia-datos/scripts/generar_resumen_metricas.py` a partir de los
artefactos ya calculados en `ciencia-datos/experimentos/`; no reproduce las 58 894 filas de las
predicciones out-of-fold, solo sus agregados. El archivo condensado vive en
`ciencia-datos/artefactos/metricas_resumen.json` (versionado en git, igual que los `.joblib`).

---

## Endpoints internos del ml-service

`srv-python` (`:8000`) **no se expone al navegador**. Se documenta aquí para depuración.

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/clasificar` | Recibe solo transacciones. Nunca ve ingreso ni deuda |
| POST | `/perfil` | Recibe solo agregados. Nunca ve descripciones crudas |
| GET | `/health` | Liveness |
| GET | `/modelo/info` | Versión, procedencia, métricas y estado de OCI |
| GET | `/modelo/metricas` | Resumen condensado de métricas de evaluación (Fase 16) |

Documentación interactiva: `http://localhost:8000/docs`

Con esa partición ningún componente de inferencia ve al usuario completo. Solo el backend
Java tiene la foto entera.
