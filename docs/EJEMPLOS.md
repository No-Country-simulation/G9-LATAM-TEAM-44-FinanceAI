# Ejemplos de uso

Siete casos ejecutados contra la API, con `srv-python` sirviendo los modelos entrenados
(`origen: local`, versión `1.0.0`). Las respuestas están copiadas tal cual salen.

Para reproducirlos:

```bash
iniciar.cmd                        # o docker compose up --build
python docs/ejemplos.py            # ejecuta los ejemplos y comprueba el resultado
```

O con la colección de Postman: `postman/FinanceAI.postman_collection.json`.

Una nota sobre el recorte: en los ejemplos de análisis se ha quitado el campo `top3` de cada
transacción, que repite la misma estructura seis veces y alarga el documento sin aportar. Su
forma completa está en el ejemplo 5. Lo demás va tal cual.

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
        {"descripcion": "Supermercado Exito", "valor": 420},
        {"descripcion": "Gasolinera Terpel", "valor": 180},
        {"descripcion": "Netflix Streaming", "valor": 40},
        {"descripcion": "Arriendo Apartamento", "valor": 900}
      ]
    }'
```

```json
{
  "perfil_financiero": "Saludable",
  "probabilidad": 0.9999,
  "resumen_gastos": {"alimentacion": 420.0, "transporte": 180.0, "ocio": 40.0, "vivienda": 900.0},
  "recomendaciones": ["Tu gasto en transporte representa el 12% del total, 1.9 veces el patrón de un perfil saludable. Es la palanca más rápida para liberar margen."],
  "factores": [
    {"nombre": "ahorro_ordinal", "valor": 3.0, "impacto": "baja_riesgo"},
    {"nombre": "ratio_endeudamiento", "valor": 0.12, "impacto": "baja_riesgo"},
    {"nombre": "tasa_gasto", "valor": 0.3422, "impacto": "baja_riesgo"}
  ],
  "transacciones_clasificadas": [
    {"descripcion": "Supermercado Exito", "valor": 420.0, "categoria": "alimentacion", "confianza": 0.9993, "estado_confianza": "aceptado"},
    {"descripcion": "Gasolinera Terpel", "valor": 180.0, "categoria": "transporte", "confianza": 0.9995, "estado_confianza": "aceptado"},
    {"descripcion": "Netflix Streaming", "valor": 40.0, "categoria": "ocio", "confianza": 0.9995, "estado_confianza": "aceptado"},
    {"descripcion": "Arriendo Apartamento", "valor": 900.0, "categoria": "vivienda", "confianza": 0.9996, "estado_confianza": "aceptado"}
  ],
  "modo_degradado": false
}
```

No hay nada estructural que corregir, así que la única recomendación apunta a la
categoría más desviada respecto al patrón de un perfil saludable.

---

## Ejemplo 2 · Usuario en observación

El margen se estrecha: gasta el 84% de lo que ingresa, la deuda pesa y ahorra poco.
Entre sus movimientos hay un pago de tarjeta, que la API categoriza como `deudas`.

```bash
curl -X POST http://localhost:8080/api/v1/analisis-financiero \
  -H "Content-Type: application/json" \
  -d '{
      "ingreso_mensual": 3000,
      "nivel_endeudamiento": 40,
      "frecuencia_ahorro": "Baja",
      "transacciones": [
        {"descripcion": "TRF/POS Supermercado Jumbo REF993021", "valor": 620},
        {"descripcion": "Uber Trip BOGOTA", "valor": 240},
        {"descripcion": "Cinepolis Entradas", "valor": 180},
        {"descripcion": "Arriendo Apartamento", "valor": 1100},
        {"descripcion": "Farmacia San Pablo", "valor": 130},
        {"descripcion": "PAGO TARJETA DE CREDITO", "valor": 260}
      ]
    }'
```

```json
{
  "perfil_financiero": "En observación",
  "probabilidad": 0.8555,
  "resumen_gastos": {"alimentacion": 620.0, "transporte": 240.0, "ocio": 180.0, "vivienda": 1100.0, "salud": 130.0, "deudas": 260.0},
  "recomendaciones": ["Gastas el 84% de tu ingreso, por encima del 58% típico de un perfil saludable.", "Tu nivel de endeudamiento (40%) alcanza o supera el 40% del ingreso. Prioriza amortizar la deuda de mayor interés antes de asumir nuevos compromisos.", "Automatiza un ahorro fijo el mismo día que recibes tu ingreso, aunque sea pequeño: para construir el hábito importa más la constancia que el monto."],
  "factores": [
    {"nombre": "pct_alimentacion", "valor": 0.2451, "impacto": "sube_riesgo"},
    {"nombre": "pct_servicios", "valor": 0.0, "impacto": "baja_riesgo"},
    {"nombre": "tasa_gasto", "valor": 0.8433, "impacto": "baja_riesgo"}
  ],
  "transacciones_clasificadas": [
    {"descripcion": "TRF/POS Supermercado Jumbo REF993021", "valor": 620.0, "categoria": "alimentacion", "confianza": 0.9995, "estado_confianza": "aceptado"},
    {"descripcion": "Uber Trip BOGOTA", "valor": 240.0, "categoria": "transporte", "confianza": 0.9987, "estado_confianza": "aceptado"},
    {"descripcion": "Cinepolis Entradas", "valor": 180.0, "categoria": "ocio", "confianza": 0.9993, "estado_confianza": "aceptado"},
    {"descripcion": "Arriendo Apartamento", "valor": 1100.0, "categoria": "vivienda", "confianza": 0.9996, "estado_confianza": "aceptado"},
    {"descripcion": "Farmacia San Pablo", "valor": 130.0, "categoria": "salud", "confianza": 0.9994, "estado_confianza": "aceptado"},
    {"descripcion": "PAGO TARJETA DE CREDITO", "valor": 260.0, "categoria": "deudas", "confianza": 0.9999, "estado_confianza": "aceptado"}
  ],
  "modo_degradado": false
}
```

Tres recomendaciones, ordenadas por impacto: primero la tasa de gasto, después la deuda
y por último el hábito de ahorro.

---

## Ejemplo 3 · Usuario en riesgo

Gasta más de lo que ingresa, con un endeudamiento del 65% y sin ahorro.

```bash
curl -X POST http://localhost:8080/api/v1/analisis-financiero \
  -H "Content-Type: application/json" \
  -d '{
      "ingreso_mensual": 2200,
      "nivel_endeudamiento": 65,
      "frecuencia_ahorro": "Nula",
      "transacciones": [
        {"descripcion": "### supermercado ara", "valor": 700},
        {"descripcion": "Bar El Callejon", "valor": 380},
        {"descripcion": "Steam Games", "valor": 210},
        {"descripcion": "Cuota Hipoteca Vivienda", "valor": 1200},
        {"descripcion": "Gasolinera Pemx", "valor": 260}
      ]
    }'
```

```json
{
  "perfil_financiero": "En riesgo",
  "probabilidad": 0.9926,
  "resumen_gastos": {"alimentacion": 700.0, "ocio": 590.0, "vivienda": 1200.0, "transporte": 260.0},
  "recomendaciones": ["Tus gastos superan tu ingreso mensual: es la prioridad número uno. Identifica los dos gastos variables más grandes y recórtalos este mes.", "Tu nivel de endeudamiento (65%) alcanza o supera el 40% del ingreso. Prioriza amortizar la deuda de mayor interés antes de asumir nuevos compromisos.", "Automatiza un ahorro fijo el mismo día que recibes tu ingreso, aunque sea pequeño: para construir el hábito importa más la constancia que el monto.", "Tu gasto en ocio representa el 21% del total, 2.8 veces el patrón de un perfil saludable. Es la palanca más rápida para liberar margen."],
  "factores": [
    {"nombre": "vivienda_sobre_ingreso", "valor": 0.5455, "impacto": "sube_riesgo"},
    {"nombre": "ratio_endeudamiento", "valor": 0.65, "impacto": "sube_riesgo"},
    {"nombre": "ahorro_ordinal", "valor": 0.0, "impacto": "sube_riesgo"}
  ],
  "transacciones_clasificadas": [
    {"descripcion": "### supermercado ara", "valor": 700.0, "categoria": "alimentacion", "confianza": 0.9994, "estado_confianza": "aceptado"},
    {"descripcion": "Bar El Callejon", "valor": 380.0, "categoria": "ocio", "confianza": 0.9994, "estado_confianza": "aceptado"},
    {"descripcion": "Steam Games", "valor": 210.0, "categoria": "ocio", "confianza": 0.9994, "estado_confianza": "aceptado"},
    {"descripcion": "Cuota Hipoteca Vivienda", "valor": 1200.0, "categoria": "vivienda", "confianza": 0.9997, "estado_confianza": "aceptado"},
    {"descripcion": "Gasolinera Pemx", "valor": 260.0, "categoria": "transporte", "confianza": 0.9989, "estado_confianza": "aceptado"}
  ],
  "modo_degradado": false
}
```

La primera descripción llega sucia (`### supermercado ara`) y aun así se clasifica bien:
de eso se encargan los n-gramas de caracteres.

---

## Ejemplo 4 · Pagos de tarjeta y cuotas

Un caso centrado en la categoría `deudas`. Incluye a propósito dos trampas: una
*Recarga Tarjeta Metro*, que lleva la palabra «tarjeta» pero es transporte, y una
*Cuota de Manejo Tarjeta*, que sí es un cargo de la tarjeta.

```bash
curl -X POST http://localhost:8080/api/v1/analisis-financiero \
  -H "Content-Type: application/json" \
  -d '{
      "ingreso_mensual": 3200,
      "nivel_endeudamiento": 30,
      "frecuencia_ahorro": "Baja",
      "transacciones": [
        {"descripcion": "PAGO TARJETA DE CREDITO", "valor": 480},
        {"descripcion": "Cuota Prestamo Bancario", "valor": 350},
        {"descripcion": "Cuota de Manejo Tarjeta", "valor": 25},
        {"descripcion": "Arriendo Apartamento", "valor": 850},
        {"descripcion": "Supermercado Exito", "valor": 390},
        {"descripcion": "Recarga Tarjeta Metro", "valor": 60}
      ]
    }'
```

```json
{
  "perfil_financiero": "Saludable",
  "probabilidad": 0.967,
  "resumen_gastos": {"deudas": 855.0, "vivienda": 850.0, "alimentacion": 390.0, "transporte": 60.0},
  "recomendaciones": ["Los pagos de deuda son el 40% de tu gasto del periodo. Concentra cualquier abono extra en la de mayor interés, normalmente la tarjeta de crédito, en lugar de repartirlo entre todas.", "Automatiza un ahorro fijo el mismo día que recibes tu ingreso, aunque sea pequeño: para construir el hábito importa más la constancia que el monto."],
  "factores": [
    {"nombre": "tasa_gasto", "valor": 0.6734, "impacto": "baja_riesgo"},
    {"nombre": "capacidad_ahorro", "valor": 0.3266, "impacto": "baja_riesgo"},
    {"nombre": "pct_deudas", "valor": 0.3968, "impacto": "baja_riesgo"}
  ],
  "transacciones_clasificadas": [
    {"descripcion": "PAGO TARJETA DE CREDITO", "valor": 480.0, "categoria": "deudas", "confianza": 0.9999, "estado_confianza": "aceptado"},
    {"descripcion": "Cuota Prestamo Bancario", "valor": 350.0, "categoria": "deudas", "confianza": 0.9996, "estado_confianza": "aceptado"},
    {"descripcion": "Cuota de Manejo Tarjeta", "valor": 25.0, "categoria": "deudas", "confianza": 0.9997, "estado_confianza": "aceptado"},
    {"descripcion": "Arriendo Apartamento", "valor": 850.0, "categoria": "vivienda", "confianza": 0.9996, "estado_confianza": "aceptado"},
    {"descripcion": "Supermercado Exito", "valor": 390.0, "categoria": "alimentacion", "confianza": 0.9993, "estado_confianza": "aceptado"},
    {"descripcion": "Recarga Tarjeta Metro", "valor": 60.0, "categoria": "transporte", "confianza": 0.9996, "estado_confianza": "aceptado"}
  ],
  "modo_degradado": false
}
```

Los pagos de deuda suman 855 y se agrupan aparte, sin mezclarse con el consumo. La
recarga del metro cae en `transporte`, como debe. Y como la deuda pesa el 40% del gasto
del periodo, aparece la recomendación de concentrar los abonos en la de mayor interés
en vez de repartirlos.

---

## Ejemplo 5 · Clasificación aislada

Cuando solo hace falta categorizar un extracto, sin diagnóstico. Este endpoint no pide
ingreso ni endeudamiento porque no los necesita.

```bash
curl -X POST http://localhost:8080/api/v1/clasificar-transacciones \
  -H "Content-Type: application/json" \
  -d '{
      "transacciones": [
        {"descripcion": "Supermercado Exito", "valor": 420},
        {"descripcion": "TRF/POS Gasolinera Terpel REF88213", "valor": 300},
        {"descripcion": "Netflix Streaming", "valor": 40},
        {"descripcion": "### farmacia cruz verde", "valor": 85},
        {"descripcion": "Avance Tarjeta de Credito", "valor": 300},
        {"descripcion": "zxqw plfj mmnb", "valor": 25}
      ]
    }'
```

```json
{
  "transacciones_clasificadas": [
    {
      "descripcion": "Supermercado Exito",
      "valor": 420.0,
      "categoria": "alimentacion",
      "confianza": 0.9993,
      "estado_confianza": "aceptado",
      "top3": [
        {"categoria": "alimentacion", "confianza": 0.9993},
        {"categoria": "servicios", "confianza": 0.0001},
        {"categoria": "educacion", "confianza": 0.0001}
      ]
    },
    {
      "descripcion": "TRF/POS Gasolinera Terpel REF88213",
      "valor": 300.0,
      "categoria": "transporte",
      "confianza": 0.9993,
      "estado_confianza": "aceptado",
      "top3": [
        {"categoria": "transporte", "confianza": 0.9993},
        {"categoria": "servicios", "confianza": 0.0002},
        {"categoria": "salud", "confianza": 0.0001}
      ]
    },
    {
      "descripcion": "Netflix Streaming",
      "valor": 40.0,
      "categoria": "ocio",
      "confianza": 0.9995,
      "estado_confianza": "aceptado",
      "top3": [
        {"categoria": "ocio", "confianza": 0.9995},
        {"categoria": "educacion", "confianza": 0.0001},
        {"categoria": "deudas", "confianza": 0.0001}
      ]
    },
    {
      "descripcion": "### farmacia cruz verde",
      "valor": 85.0,
      "categoria": "salud",
      "confianza": 0.9995,
      "estado_confianza": "aceptado",
      "top3": [
        {"categoria": "salud", "confianza": 0.9995},
        {"categoria": "deudas", "confianza": 0.0001},
        {"categoria": "servicios", "confianza": 0.0001}
      ]
    },
    {
      "descripcion": "Avance Tarjeta de Credito",
      "valor": 300.0,
      "categoria": "deudas",
      "confianza": 0.9998,
      "estado_confianza": "aceptado",
      "top3": [
        {"categoria": "deudas", "confianza": 0.9998},
        {"categoria": "educacion", "confianza": 0.0},
        {"categoria": "ocio", "confianza": 0.0}
      ]
    },
    {
      "descripcion": "zxqw plfj mmnb",
      "valor": 25.0,
      "categoria": "otras",
      "confianza": 0.4736,
      "estado_confianza": "otras",
      "top3": [
        {"categoria": "otras", "confianza": 0.4736},
        {"categoria": "alimentacion", "confianza": 0.4736},
        {"categoria": "ocio", "confianza": 0.1782}
      ]
    }
  ],
  "resumen_gastos": {"alimentacion": 420.0, "transporte": 300.0, "ocio": 40.0, "salud": 85.0, "deudas": 300.0, "otras": 25.0},
  "total_gastos": 1170.0,
  "modo_degradado": false
}
```

La última transacción no se parece a nada conocido: la confianza cae por debajo del
umbral de 0.5 y acaba en `otras` en lugar de forzar una categoría.

---

## Ejemplo 6 · Validación de entrada

Los errores se reportan todos a la vez, campo por campo, en lugar de uno por petición.

```bash
curl -X POST http://localhost:8080/api/v1/analisis-financiero \
  -H "Content-Type: application/json" \
  -d '{
      "ingreso_mensual": 0,
      "nivel_endeudamiento": 150,
      "frecuencia_ahorro": "Siempre",
      "transacciones": []
    }'
```

```json
{
  "mensaje": "Error de validación en los campos enviados",
  "codigo_estado": 400,
  "timestamp": "2026-08-24T22:02:38.0713924",
  "detalles": {"nivelEndeudamiento": "El nivel de endeudamiento es un porcentaje: maximo 100", "transacciones": "Se requiere entre 1 y 5000 transacciones", "frecuenciaAhorro": "La frecuencia de ahorro debe ser Alta, Media, Baja o Nula", "ingresoMensual": "El ingreso mensual debe ser mayor a 0"}
}
```

---

## Ejemplo 7 · El ml-service caído

Se apaga `srv-python` y se repite el ejemplo 1:

```bash
docker compose stop ml-service
```

```json
{
  "perfil_financiero": "Saludable",
  "probabilidad": 0.9,
  "resumen_gastos": {"alimentacion": 420.0, "transporte": 180.0, "ocio": 40.0, "vivienda": 900.0},
  "recomendaciones": ["Tu gasto en transporte representa el 12% del total, 1.9 veces el patrón de un perfil saludable. Es la palanca más rápida para liberar margen."],
  "factores": [
    {"nombre": "relacion_deuda_ingreso", "valor": 0.12, "impacto": "baja_riesgo"},
    {"nombre": "tasa_gasto", "valor": 0.342, "impacto": "baja_riesgo"},
    {"nombre": "frecuencia_ahorro", "valor": 1.0, "impacto": "baja_riesgo"}
  ],
  "transacciones_clasificadas": [
    {"descripcion": "Supermercado Exito", "valor": 420.0, "categoria": "alimentacion", "confianza": 0.9, "estado_confianza": "aceptado"},
    {"descripcion": "Gasolinera Terpel", "valor": 180.0, "categoria": "transporte", "confianza": 0.9, "estado_confianza": "aceptado"},
    {"descripcion": "Netflix Streaming", "valor": 40.0, "categoria": "ocio", "confianza": 0.9, "estado_confianza": "aceptado"},
    {"descripcion": "Arriendo Apartamento", "valor": 900.0, "categoria": "vivienda", "confianza": 0.9, "estado_confianza": "aceptado"}
  ],
  "modo_degradado": true
}
```

No hay 5xx. La API usa el clasificador por palabras clave y los umbrales locales, y lo declara
con `modo_degradado: true`. La respuesta tiene la misma forma, así que el frontend solo
muestra el aviso de resultado aproximado.

Para forzar este modo sin apagar nada: `ML_SERVICE_ENABLED=false`.
