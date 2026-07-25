# Endpoints Finance AI API

Base URL local: `http://localhost:8080`

| Método | Endpoint | Descripción |
|---|---|---|
| GET | /api/v1/health | Liveness de la API (no consulta el ml-service) |
| GET | /api/v1/version | Versión del MVP |
| GET | /api/v1/ml-status | Si el servicio de AI (srv-python) está accesible |
| POST | /api/v1/analisis-financiero | Análisis financiero completo |

Swagger: `/swagger-ui.html` · OpenAPI JSON: `/api-docs`

Todo el JSON va en **snake_case** (`spring.jackson.property-naming-strategy=SNAKE_CASE`).

---

## POST /api/v1/analisis-financiero

### Petición

```json
{
  "ingreso_mensual": 4500,
  "nivel_endeudamiento": 25,
  "frecuencia_ahorro": "Media",
  "transacciones": [
    { "descripcion": "Supermercado Exito", "valor": 420 },
    { "descripcion": "Gasolina Terpel", "valor": 300 },
    { "descripcion": "Netflix", "valor": 40 }
  ]
}
```

Restricciones (alineadas con el contrato de srv-python, para responder 400 en
vez de dejar que Python responda 422):

| Campo | Regla |
|---|---|
| `ingreso_mensual` | requerido, > 0 |
| `nivel_endeudamiento` | requerido, entero entre 0 y 100 |
| `frecuencia_ahorro` | requerido: `Alta`, `Media`, `Baja` o `Nula` |
| `transacciones` | requerido, entre 1 y 5000 elementos |
| `transacciones[].descripcion` | requerido, máx. 200 caracteres |
| `transacciones[].valor` | requerido, > 0 |

### Respuesta 200

```json
{
  "perfil_financiero": "Saludable",
  "probabilidad": 0.9,
  "resumen_gastos": {
    "alimentacion": 420.0,
    "transporte": 300.0,
    "ocio": 40.0
  },
  "recomendaciones": [
    "Mantener el control de gastos y continuar monitoreando la evolución financiera."
  ],
  "factores": [
    { "nombre": "relacion_deuda_ingreso", "valor": 0.25, "impacto": "baja_riesgo" },
    { "nombre": "tasa_gasto",             "valor": 0.172, "impacto": "baja_riesgo" },
    { "nombre": "frecuencia_ahorro",      "valor": 1.0,  "impacto": "baja_riesgo" }
  ],
  "modo_degradado": false
}
```

**`modo_degradado`** es el campo clave para el frontend:

- `false` → el resultado viene de los modelos en srv-python.
- `true` → srv-python no respondió y el análisis se calculó con las reglas de
  respaldo locales. La respuesta sigue siendo válida y con la misma forma; solo
  conviene mostrar un aviso del tipo "resultado aproximado".

`impacto` siempre es `sube_riesgo` o `baja_riesgo`.

Categorías canónicas de `resumen_gastos`:
`alimentacion · transporte · salud · vivienda · educacion · ocio · servicios · otras`

Perfiles: `Saludable · En observación · En riesgo`

### Respuesta 400 (validación)

```json
{
  "mensaje": "Error de validación en los campos enviados",
  "codigo_estado": 400,
  "timestamp": "2026-07-24T20:10:54.219",
  "detalles": {
    "ingresoMensual": "El ingreso mensual debe ser mayor a 0",
    "frecuenciaAhorro": "La frecuencia de ahorro debe ser Alta, Media, Baja o Nula"
  }
}
```

Nota: las claves de `detalles` son los nombres de los campos Java (camelCase),
no los del JSON. Es el comportamiento por defecto de Bean Validation.

---

## GET /api/v1/ml-status

```json
{
  "ml_service_url": "http://localhost:8000",
  "disponible": true,
  "modo": "modelo"
}
```

Útil para diagnosticar la integración sin mirar los logs.
