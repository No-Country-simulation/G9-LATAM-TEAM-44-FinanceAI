# Matriz de confusion sobre predicciones OOD (out-of-fold)

Construida sobre 58,894 predicciones out-of-fold de `ciencia-datos/experimentos/oof_predicciones_cv.csv` (Fase 2: StratifiedGroupKFold(n_splits=5) agrupado por comercio). Cada prediccion fue hecha por un modelo que nunca vio ese comercio en entrenamiento, por lo que estas confusiones reflejan el comportamiento del clasificador ante comercios no vistos (out-of-distribution relativo a cada fold).

Accuracy global sobre el OOF (diagonal / total): 0.4264

## Matriz de confusion (filas = real, columnas = predicha)

| real \ predicha | alimentacion | transporte | salud | vivienda | educacion | ocio | servicios | otras |
|---|---|---|---|---|---|---|---|---|
| **alimentacion** | 3449 | 200 | 4 | 228 | 125 | 638 | 179 | 898 |
| **transporte** | 1209 | 2833 | 6 | 532 | 236 | 342 | 293 | 496 |
| **salud** | 276 | 41 | 3806 | 2363 | 315 | 314 | 4 | 914 |
| **vivienda** | 1233 | 383 | 749 | 3537 | 1 | 405 | 753 | 2023 |
| **educacion** | 912 | 509 | 478 | 4 | 1801 | 1464 | 1 | 791 |
| **ocio** | 1925 | 310 | 238 | 482 | 1329 | 4366 | 230 | 300 |
| **servicios** | 1629 | 1492 | 15 | 542 | 464 | 714 | 4345 | 28 |
| **otras** | 2293 | 1048 | 257 | 273 | 279 | 601 | 12 | 977 |

## Confusiones mas frecuentes (fuera de la diagonal)

Ordenadas por proporcion de la fila real (que fraccion de esa categoria real termino predicha como otra categoria).

| real | predicha | casos | % de la fila real | total fila real |
|---|---|---|---|---|
| otras | alimentacion | 2,293 | 39.9477% | 5,740 |
| salud | vivienda | 2,363 | 29.4162% | 8,033 |
| educacion | ocio | 1,464 | 24.5638% | 5,960 |
| vivienda | otras | 2,023 | 22.2699% | 9,084 |
| ocio | alimentacion | 1,925 | 20.9695% | 9,180 |
| transporte | alimentacion | 1,209 | 20.3296% | 5,947 |
| otras | transporte | 1,048 | 18.2578% | 5,740 |
| servicios | alimentacion | 1,629 | 17.6509% | 9,229 |

## Distribucion real vs. predicha por categoria

Si el clasificador generalizara bien a comercios no vistos, la columna de filas predichas deberia parecerse a la de filas reales. Una razon > 1 indica una categoria que actua como "iman" (recibe mas predicciones de las que le corresponden); una razon < 1 indica una categoria subrepresentada en las predicciones.

| categoria | filas reales | filas predichas | razon predichas/reales |
|---|---|---|---|
| alimentacion | 5,721 | 12,926 | 2.2594 |
| transporte | 5,947 | 6,816 | 1.1461 |
| salud | 8,033 | 5,553 | 0.6913 |
| vivienda | 9,084 | 7,961 | 0.8764 |
| educacion | 5,960 | 4,550 | 0.7634 |
| ocio | 9,180 | 8,844 | 0.9634 |
| servicios | 9,229 | 5,817 | 0.6303 |
| otras | 5,740 | 6,427 | 1.1197 |

## Analisis

Para cada confusion se listan los comercios (nunca vistos por el modelo en ese fold, por la agrupacion de la CV) que mas casos aportan a esa celda, junto con que fraccion de TODAS las filas de ese comercio en el OOF cayeron ahi. Cuando esa fraccion es cercana a 1.0, no se trata de una confusion parcial dentro de una categoria heterogenea, sino de un comercio completo que el modelo redirige casi siempre hacia la misma categoria equivocada al no reconocer ninguno de sus tokens exactos.

### otras -> alimentacion (2,293 casos, 39.9477% de las filas reales de `otras`)

- `Comision Bancaria`: 305 de sus 307 filas en el OOF cayeron en esta celda (99.3485% de ese comercio).
- `Compra Marketplace`: 304 de sus 307 filas en el OOF cayeron en esta celda (99.0228% de ese comercio).
- `Lavanderia Express`: 301 de sus 301 filas en el OOF cayeron en esta celda (100.0000% de ese comercio).

### salud -> vivienda (2,363 casos, 29.4162% de las filas reales de `salud`)

- `EPS Cuota Moderadora`: 1,838 de sus 2,653 filas en el OOF cayeron en esta celda (69.2801% de ese comercio).
- `Medicamentos Recetados`: 319 de sus 338 filas en el OOF cayeron en esta celda (94.3787% de ese comercio).
- `Optica Vision Center`: 206 de sus 292 filas en el OOF cayeron en esta celda (70.5479% de ese comercio).

### educacion -> ocio (1,464 casos, 24.5638% de las filas reales de `educacion`)

- `Suscripcion Platzi`: 513 de sus 514 filas en el OOF cayeron en esta celda (99.8054% de ese comercio).
- `Curso Udemy Online`: 452 de sus 482 filas en el OOF cayeron en esta celda (93.7759% de ese comercio).
- `Pension Colegio`: 392 de sus 464 filas en el OOF cayeron en esta celda (84.4828% de ese comercio).

### vivienda -> otras (2,023 casos, 22.2699% de las filas reales de `vivienda`)

- `Cuota Hipoteca Vivienda`: 1,432 de sus 1,491 filas en el OOF cayeron en esta celda (96.0429% de ese comercio).
- `Reparacion Plomeria`: 367 de sus 394 filas en el OOF cayeron en esta celda (93.1472% de ese comercio).
- `Administracion Edificio`: 174 de sus 1,464 filas en el OOF cayeron en esta celda (11.8852% de ese comercio).

### ocio -> alimentacion (1,925 casos, 20.9695% de las filas reales de `ocio`)

- `Gimnasio SmartFit`: 828 de sus 1,061 filas en el OOF cayeron en esta celda (78.0396% de ese comercio).
- `Restaurante Gourmet`: 239 de sus 239 filas en el OOF cayeron en esta celda (100.0000% de ese comercio).
- `Bar El Callejon`: 233 de sus 248 filas en el OOF cayeron en esta celda (93.9516% de ese comercio).

### transporte -> alimentacion (1,209 casos, 20.3296% de las filas reales de `transporte`)

- `Shell Combustible`: 243 de sus 249 filas en el OOF cayeron en esta celda (97.5904% de ese comercio).
- `Taxi Amarillo`: 233 de sus 254 filas en el OOF cayeron en esta celda (91.7323% de ese comercio).
- `DiDi Ride`: 233 de sus 251 filas en el OOF cayeron en esta celda (92.8287% de ese comercio).

### otras -> transporte (1,048 casos, 18.2578% de las filas reales de `otras`)

- `Transferencia a Terceros`: 294 de sus 300 filas en el OOF cayeron en esta celda (98.0000% de ese comercio).
- `Retiro Cajero Automatico`: 270 de sus 270 filas en el OOF cayeron en esta celda (100.0000% de ese comercio).
- `Impuesto Retencion`: 258 de sus 315 filas en el OOF cayeron en esta celda (81.9048% de ese comercio).

### servicios -> alimentacion (1,629 casos, 17.6509% de las filas reales de `servicios`)

- `Gas Natural Domiciliario`: 1,080 de sus 1,080 filas en el OOF cayeron en esta celda (100.0000% de ese comercio).
- `Almacenamiento iCloud`: 410 de sus 410 filas en el OOF cayeron en esta celda (100.0000% de ese comercio).
- `Claro Telefonia Movil`: 74 de sus 1,035 filas en el OOF cayeron en esta celda (7.1498% de ese comercio).

### Hipotesis

1. **El texto es casi puramente el nombre del comercio, no vocabulario generico de la categoria.** `descripcion_limpia` es en la practica el nombre del comercio (con erratas/variantes), por lo que el vectorizador aprende, sobre todo, tokens y n-gramas de caracteres asociados a cada comercio particular en vez de un vocabulario compartido por categoria. Cuando un comercio queda fuera del entrenamiento de un fold (por la agrupacion `StratifiedGroupKFold` sobre `comercio`), el modelo no tiene ninguna fila con esos tokens exactos y debe decidir en base a coincidencias parciales de n-gramas de caracteres (3-5) con comercios de OTRAS categorias, lo que produce el patron observado: comercios completos (95-100% de sus filas) migran en bloque hacia una unica categoria equivocada (ej. `EPS Cuota Moderadora` -> vivienda en 69% de sus filas, `Gas Natural Domiciliario` -> alimentacion en el 100%, `Cuota Hipoteca Vivienda` -> otras en 96%).
2. **`alimentacion` actua como categoria iman para texto no reconocido.** Es la categoria real MENOS frecuente en el OOF (la mas chica de las 8) pero la MAS predicha con amplio margen (mas del doble de veces de las que realmente ocurre), ver tabla de distribucion arriba. Esto sugiere que, ante un comercio sin ningun n-grama reconocible, la funcion de decision calibrada (`CalibratedClassifierCV` sobre `LinearSVC`) tiende a favorecer `alimentacion` como opcion por defecto, probablemente porque en el vocabulario de esa categoria abundan palabras y fragmentos de caracteres cortos y comunes en español (ej. sufijos, numeros, nombres de ciudad que tambien aparecen en las erratas de otros comercios) que generalizan mal como señal discriminativa.
3. **Los pares confundidos no comparten un tema de gasto obvio (salud/vivienda, educacion/ocio, servicios/alimentacion), lo que refuerza la hipotesis 1**: si la confusion fuera por vocabulario semanticamente cercano (dos categorias de gasto parecidas), esperariamos ver pares tematicamente relacionados. En cambio, el patron dominante es "un comercio especifico, no visto, cae entero en una categoria arbitraria", consistente con sobreajuste a nombres de comercio en vez de aprender categorias generalizables.
