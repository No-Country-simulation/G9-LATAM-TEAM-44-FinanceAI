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
| `modo_degradado` | `true` = calculado con reglas locales, no con el modelo |

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
    { "descripcion": "Supermercado Exito",                 "valor": 420.0, "categoria": "alimentacion", "confianza": 0.9993 },
    { "descripcion": "TRF/POS Gasolinera Terpel REF88213",  "valor": 300.0, "categoria": "transporte",   "confianza": 0.9994 },
    { "descripcion": "Netflix Streaming",                   "valor": 40.0,  "categoria": "ocio",         "confianza": 0.9995 },
    { "descripcion": "### farmacia cruz verde",             "valor": 85.0,  "categoria": "salud",        "confianza": 0.9996 },
    { "descripcion": "zxqw plfj mmnb",                      "valor": 25.0,  "categoria": "otras",        "confianza": 0.3573 }
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

### Categorías

`alimentacion` · `transporte` · `salud` · `vivienda` · `educacion` · `ocio` · `servicios` · `otras`

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
    "entrenado_en": "2026-08-17T17:49:00",
    "metricas": {
      "clasificador_particion_aleatoria":  { "accuracy": 0.9999, "f1_macro": 0.9999 },
      "clasificador_comercios_no_vistos":  { "accuracy": 0.4111, "f1_macro": 0.4181 },
      "perfil_cv_agrupada":                { "accuracy": 0.8692, "f1_macro": 0.8613 }
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

## Endpoints internos del ml-service

`srv-python` (`:8000`) **no se expone al navegador**. Se documenta aquí para depuración.

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/clasificar` | Recibe solo transacciones. Nunca ve ingreso ni deuda |
| POST | `/perfil` | Recibe solo agregados. Nunca ve descripciones crudas |
| GET | `/health` | Liveness |
| GET | `/modelo/info` | Versión, procedencia, métricas y estado de OCI |

Documentación interactiva: `http://localhost:8000/docs`

Con esa partición ningún componente de inferencia ve al usuario completo. Solo el backend
Java tiene la foto entera.
