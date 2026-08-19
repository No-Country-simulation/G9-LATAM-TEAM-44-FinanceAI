# Ejemplos de uso

Seis casos ejecutados contra la API, con `srv-python` sirviendo los modelos entrenados
(`origen: local`, versión `1.0.0`). Las respuestas están copiadas tal cual salen.

Para reproducirlos:

```bash
iniciar.cmd                        # o docker compose up --build
python docs/ejemplos.py            # ejecuta los ejemplos y muestra las respuestas
```

O con la colección de Postman: `postman/FinanceAI.postman_collection.json`.

---

## Ejemplo 1 · Usuario con finanzas sanas

Gasta el 34% de su ingreso, se endeuda poco y ahorra con frecuencia.

```bash
curl -X POST http://localhost:8080/api/v1/analisis-financiero \
  -H "Content-Type: application/json" \
  -d '{
    "ingreso_mensual": 4500,
    "nivel_endeudamiento": 12,
    "frecuencia_ahorro": "Alta",
    "transacciones": [
      {"descripcion": "Supermercado Exito",   "valor": 420},
      {"descripcion": "Gasolinera Terpel",    "valor": 180},
      {"descripcion": "Netflix Streaming",    "valor": 40},
      {"descripcion": "Arriendo Apartamento", "valor": 900}
    ]
  }'
```

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

Aun con el perfil sano, sale algo sobre lo que actuar: el transporte pesa casi el doble de lo
normal.

---

## Ejemplo 2 · Usuario en observación

Gasta el 76% de su ingreso y arrastra un endeudamiento del 35%. Todavía no es crítico, pero
el margen se está estrechando.

La primera transacción llega con el formato sucio de un extracto real
(`TRF/POS … REF993021`) y se clasifica igual.

```bash
curl -X POST http://localhost:8080/api/v1/analisis-financiero \
  -H "Content-Type: application/json" \
  -d '{
    "ingreso_mensual": 3000,
    "nivel_endeudamiento": 35,
    "frecuencia_ahorro": "Media",
    "transacciones": [
      {"descripcion": "TRF/POS Supermercado Jumbo REF993021", "valor": 620},
      {"descripcion": "Uber Trip BOGOTA",                     "valor": 240},
      {"descripcion": "Cinepolis Entradas",                   "valor": 180},
      {"descripcion": "Arriendo Apartamento",                 "valor": 1100},
      {"descripcion": "Farmacia San Pablo",                   "valor": 130}
    ]
  }'
```

```json
{
  "perfil_financiero": "En observación",
  "probabilidad": 0.6655,
  "resumen_gastos": {
    "alimentacion": 620.0,
    "transporte": 240.0,
    "ocio": 180.0,
    "vivienda": 1100.0,
    "salud": 130.0
  },
  "recomendaciones": [
    "Gastas el 76% de tu ingreso, por encima del 58% típico de un perfil saludable.",
    "Tu gasto en transporte representa el 11% del total, 1.7 veces el patrón de un perfil saludable. Es la palanca más rápida para liberar margen."
  ],
  "factores": [
    { "nombre": "ahorro_ordinal",   "valor": 2.0,    "impacto": "baja_riesgo" },
    { "nombre": "pct_alimentacion", "valor": 0.2731, "impacto": "sube_riesgo" },
    { "nombre": "ratio_endeudamiento", "valor": 0.35, "impacto": "baja_riesgo" }
  ],
  "modo_degradado": false
}
```

La probabilidad baja a 0.67. Tiene sentido: `En observación` es la banda intermedia y el
notebook muestra que es la clase más difícil de separar.

El tercer factor puede despistar: 35% de endeudamiento aparece como `baja_riesgo` porque el
impacto se mide frente al usuario promedio, y 35% está por debajo de la media del conjunto de
entrenamiento. Está explicado en [API-ENDPOINTS.md](../srv-java/docs/API-ENDPOINTS.md).

---

## Ejemplo 3 · Usuario en riesgo

Gasta 2.750 con un ingreso de 2.200 —el 125%—, debe el 65% y no ahorra nunca. Una de las
descripciones llega con basura al principio (`### supermercado ara`) y otra con el nombre del
comercio mal escrito (`Gasolinera Pemx` en vez de *Pemex*). Ambas se clasifican bien: los
n-gramas de caracteres del vectorizador absorben ese ruido.

```bash
curl -X POST http://localhost:8080/api/v1/analisis-financiero \
  -H "Content-Type: application/json" \
  -d '{
    "ingreso_mensual": 2200,
    "nivel_endeudamiento": 65,
    "frecuencia_ahorro": "Nula",
    "transacciones": [
      {"descripcion": "### supermercado ara",     "valor": 700},
      {"descripcion": "Bar El Callejon",          "valor": 380},
      {"descripcion": "Steam Games",              "valor": 210},
      {"descripcion": "Cuota Hipoteca Vivienda",  "valor": 1200},
      {"descripcion": "Gasolinera Pemx",          "valor": 260}
    ]
  }'
```

```json
{
  "perfil_financiero": "En riesgo",
  "probabilidad": 0.9991,
  "resumen_gastos": {
    "alimentacion": 700.0,
    "ocio": 590.0,
    "vivienda": 1200.0,
    "transporte": 260.0
  },
  "recomendaciones": [
    "Tus gastos superan tu ingreso mensual: es la prioridad número uno. Identifica los dos gastos variables más grandes y recórtalos este mes.",
    "Tu nivel de endeudamiento (65%) supera el 40% del ingreso. Prioriza amortizar la deuda de mayor interés antes de asumir nuevos compromisos.",
    "Automatiza un ahorro fijo el mismo día que recibes tu ingreso, aunque sea pequeño: para construir el hábito importa más la constancia que el monto.",
    "Tu gasto en ocio representa el 21% del total, 2.8 veces el patrón de un perfil saludable. Es la palanca más rápida para liberar margen."
  ],
  "factores": [
    { "nombre": "vivienda_sobre_ingreso", "valor": 0.5455, "impacto": "sube_riesgo" },
    { "nombre": "ratio_endeudamiento",    "valor": 0.65,   "impacto": "sube_riesgo" },
    { "nombre": "ahorro_ordinal",         "valor": 0.0,    "impacto": "sube_riesgo" }
  ],
  "modo_degradado": false
}
```

Las recomendaciones salen ordenadas por impacto: primero gastar más de lo que se ingresa,
después la deuda, después el hábito de ahorro y al final la categoría concreta.
`Bar El Callejon` y `Steam Games` suman 590 en ocio, el 21% del gasto frente al 9% de un
perfil saludable.

---

## Ejemplo 4 · Clasificación aislada

Cuando solo hace falta categorizar un extracto, sin diagnóstico. Este endpoint no pide
ingreso ni endeudamiento porque no los necesita.

```bash
curl -X POST http://localhost:8080/api/v1/clasificar-transacciones \
  -H "Content-Type: application/json" \
  -d '{
    "transacciones": [
      {"descripcion": "Supermercado Exito",                  "valor": 420},
      {"descripcion": "TRF/POS Gasolinera Terpel REF88213",  "valor": 300},
      {"descripcion": "Netflix Streaming",                   "valor": 40},
      {"descripcion": "### farmacia cruz verde",             "valor": 85},
      {"descripcion": "zxqw plfj mmnb",                      "valor": 25}
    ]
  }'
```

```json
{
  "transacciones_clasificadas": [
    { "descripcion": "Supermercado Exito",                 "valor": 420.0, "categoria": "alimentacion", "confianza": 0.9993 },
    { "descripcion": "TRF/POS Gasolinera Terpel REF88213", "valor": 300.0, "categoria": "transporte",   "confianza": 0.9994 },
    { "descripcion": "Netflix Streaming",                  "valor": 40.0,  "categoria": "ocio",         "confianza": 0.9995 },
    { "descripcion": "### farmacia cruz verde",            "valor": 85.0,  "categoria": "salud",        "confianza": 0.9996 },
    { "descripcion": "zxqw plfj mmnb",                     "valor": 25.0,  "categoria": "otras",        "confianza": 0.3573 }
  ],
  "resumen_gastos": {
    "alimentacion": 420.0, "transporte": 300.0, "ocio": 40.0, "salud": 85.0, "otras": 25.0
  },
  "total_gastos": 870.0,
  "modo_degradado": false
}
```

La quinta transacción no se parece a nada conocido: la confianza cae a 0.36 y el umbral la
manda a `otras` en vez de forzar una categoría.

---

## Ejemplo 5 · Validación de entrada

Los errores se reportan todos a la vez, campo por campo, en lugar de uno por petición.

```bash
curl -X POST http://localhost:8080/api/v1/analisis-financiero \
  -H "Content-Type: application/json" \
  -d '{"ingreso_mensual": 0, "nivel_endeudamiento": 150, "frecuencia_ahorro": "Siempre", "transacciones": []}'
```

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

---

## Ejemplo 6 · El ml-service caído

Se apaga `srv-python` y se repite el ejemplo 1:

```bash
docker compose stop ml-service
```

```json
{
  "perfil_financiero": "Saludable",
  "probabilidad": 0.9,
  "resumen_gastos": { "alimentacion": 420.0, "transporte": 180.0, "ocio": 40.0, "vivienda": 900.0 },
  "recomendaciones": ["..."],
  "factores": [
    { "nombre": "relacion_deuda_ingreso", "valor": 0.12, "impacto": "baja_riesgo" },
    { "nombre": "tasa_gasto",             "valor": 0.34, "impacto": "baja_riesgo" },
    { "nombre": "frecuencia_ahorro",      "valor": 1.0,  "impacto": "baja_riesgo" }
  ],
  "modo_degradado": true
}
```

No hay 5xx. La API usa el clasificador por palabras clave y los umbrales locales, y lo declara
con `modo_degradado: true`. La respuesta tiene la misma forma, así que el frontend solo
muestra el aviso de resultado aproximado.

Para forzar este modo sin apagar nada: `ML_SERVICE_ENABLED=false`.
