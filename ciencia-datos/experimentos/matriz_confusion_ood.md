# Matriz de confusion sobre predicciones OOD (out-of-fold)

Construida sobre 63,309 predicciones out-of-fold de `ciencia-datos/experimentos/oof_predicciones_cv.csv` (Fase 2: StratifiedGroupKFold(n_splits=5) agrupado por comercio). Cada prediccion fue hecha por un modelo que nunca vio ese comercio en entrenamiento, por lo que estas confusiones reflejan el comportamiento del clasificador ante comercios no vistos (out-of-distribution relativo a cada fold).

Accuracy global sobre el OOF (diagonal / total): 0.3977

## Matriz de confusion (filas = real, columnas = predicha)

| real \ predicha | alimentacion | transporte | salud | vivienda | educacion | ocio | servicios | deudas | otras |
|---|---|---|---|---|---|---|---|---|---|
| **alimentacion** | 3908 | 194 | 5 | 154 | 203 | 448 | 23 | 0 | 951 |
| **transporte** | 1444 | 1924 | 9 | 252 | 242 | 274 | 469 | 447 | 757 |
| **salud** | 23 | 89 | 3212 | 592 | 607 | 20 | 7 | 2566 | 971 |
| **vivienda** | 1809 | 886 | 344 | 3469 | 5 | 75 | 735 | 1021 | 818 |
| **educacion** | 555 | 978 | 505 | 0 | 1953 | 1432 | 7 | 0 | 540 |
| **ocio** | 1766 | 507 | 207 | 420 | 1236 | 4509 | 382 | 0 | 253 |
| **servicios** | 2076 | 739 | 8 | 2641 | 812 | 70 | 2232 | 801 | 59 |
| **deudas** | 15 | 307 | 1 | 0 | 0 | 1 | 129 | 3291 | 21 |
| **otras** | 2424 | 1170 | 571 | 363 | 0 | 677 | 4 | 12 | 682 |

## Confusiones mas frecuentes (fuera de la diagonal)

Ordenadas por proporcion de la fila real (que fraccion de esa categoria real termino predicha como otra categoria).

| real | predicha | casos | % de la fila real | total fila real |
|---|---|---|---|---|
| otras | alimentacion | 2,424 | 41.0639% | 5,903 |
| salud | deudas | 2,566 | 31.7299% | 8,087 |
| servicios | vivienda | 2,641 | 27.9826% | 9,438 |
| transporte | alimentacion | 1,444 | 24.8195% | 5,818 |
| educacion | ocio | 1,432 | 23.9866% | 5,970 |
| servicios | alimentacion | 2,076 | 21.9962% | 9,438 |
| otras | transporte | 1,170 | 19.8204% | 5,903 |
| vivienda | alimentacion | 1,809 | 19.7446% | 9,162 |

## Distribucion real vs. predicha por categoria

Si el clasificador generalizara bien a comercios no vistos, la columna de filas predichas deberia parecerse a la de filas reales. Una razon > 1 indica una categoria que actua como "iman" (recibe mas predicciones de las que le corresponden); una razon < 1 indica una categoria subrepresentada en las predicciones.

| categoria | filas reales | filas predichas | razon predichas/reales |
|---|---|---|---|
| alimentacion | 5,886 | 14,020 | 2.3819 |
| transporte | 5,818 | 6,794 | 1.1678 |
| salud | 8,087 | 4,862 | 0.6012 |
| vivienda | 9,162 | 7,891 | 0.8613 |
| educacion | 5,970 | 5,058 | 0.8472 |
| ocio | 9,280 | 7,506 | 0.8088 |
| servicios | 9,438 | 3,988 | 0.4225 |
| deudas | 3,765 | 8,138 | 2.1615 |
| otras | 5,903 | 5,052 | 0.8558 |

## Analisis

Para cada confusion se listan los comercios (nunca vistos por el modelo en ese fold, por la agrupacion de la CV) que mas casos aportan a esa celda, junto con que fraccion de TODAS las filas de ese comercio en el OOF cayeron ahi. Cuando esa fraccion es cercana a 1.0, no se trata de una confusion parcial dentro de una categoria heterogenea, sino de un comercio completo que el modelo redirige casi siempre hacia la misma categoria equivocada al no reconocer ninguno de sus tokens exactos.

### otras -> alimentacion (2,424 casos, 41.0639% de las filas reales de `otras`)

- `Perfumeria Belleza`: 320 de sus 321 filas en el OOF cayeron en esta celda (99.6885% de ese comercio).
- `Mercado Libre Compra`: 308 de sus 308 filas en el OOF cayeron en esta celda (100.0000% de ese comercio).
- `Compra Marketplace`: 295 de sus 295 filas en el OOF cayeron en esta celda (100.0000% de ese comercio).

### salud -> deudas (2,566 casos, 31.7299% de las filas reales de `salud`)

- `EPS Cuota Moderadora`: 2,566 de sus 2,639 filas en el OOF cayeron en esta celda (97.2338% de ese comercio).

### servicios -> vivienda (2,641 casos, 27.9826% de las filas reales de `servicios`)

- `Movistar Internet Hogar`: 1,138 de sus 1,156 filas en el OOF cayeron en esta celda (98.4429% de ese comercio).
- `Servicio Agua Potable`: 1,056 de sus 1,056 filas en el OOF cayeron en esta celda (100.0000% de ese comercio).
- `Antivirus Licencia Anual`: 407 de sus 433 filas en el OOF cayeron en esta celda (93.9954% de ese comercio).

### transporte -> alimentacion (1,444 casos, 24.8195% de las filas reales de `transporte`)

- `DiDi Ride`: 263 de sus 265 filas en el OOF cayeron en esta celda (99.2453% de ese comercio).
- `Uber Trip`: 252 de sus 252 filas en el OOF cayeron en esta celda (100.0000% de ese comercio).
- `Shell Combustible`: 244 de sus 246 filas en el OOF cayeron en esta celda (99.1870% de ese comercio).

### educacion -> ocio (1,432 casos, 23.9866% de las filas reales de `educacion`)

- `Suscripcion Platzi`: 485 de sus 486 filas en el OOF cayeron en esta celda (99.7942% de ese comercio).
- `Utiles Escolares`: 483 de sus 493 filas en el OOF cayeron en esta celda (97.9716% de ese comercio).
- `Pension Colegio`: 419 de sus 457 filas en el OOF cayeron en esta celda (91.6849% de ese comercio).

### servicios -> alimentacion (2,076 casos, 21.9962% de las filas reales de `servicios`)

- `Gas Natural Domiciliario`: 1,170 de sus 1,170 filas en el OOF cayeron en esta celda (100.0000% de ese comercio).
- `Almacenamiento iCloud`: 408 de sus 422 filas en el OOF cayeron en esta celda (96.6825% de ese comercio).
- `Tigo Une Plan`: 407 de sus 425 filas en el OOF cayeron en esta celda (95.7647% de ese comercio).

### otras -> transporte (1,170 casos, 19.8204% de las filas reales de `otras`)

- `Retiro Cajero Automatico`: 311 de sus 311 filas en el OOF cayeron en esta celda (100.0000% de ese comercio).
- `Regalo Cumpleanos`: 298 de sus 315 filas en el OOF cayeron en esta celda (94.6032% de ese comercio).
- `Transferencia a Terceros`: 292 de sus 296 filas en el OOF cayeron en esta celda (98.6486% de ese comercio).

### vivienda -> alimentacion (1,809 casos, 19.7446% de las filas reales de `vivienda`)

- `Cuota Hipoteca Vivienda`: 559 de sus 1,582 filas en el OOF cayeron en esta celda (35.3350% de ese comercio).
- `Impuesto Predial`: 405 de sus 412 filas en el OOF cayeron en esta celda (98.3010% de ese comercio).
- `Ferreteria El Martillo`: 381 de sus 386 filas en el OOF cayeron en esta celda (98.7047% de ese comercio).

### Hipotesis

1. **El texto es casi puramente el nombre del comercio, no vocabulario generico de la categoria.** `descripcion_limpia` es en la practica el nombre del comercio (con erratas/variantes), por lo que el vectorizador aprende, sobre todo, tokens y n-gramas de caracteres asociados a cada comercio particular en vez de un vocabulario compartido por categoria. Cuando un comercio queda fuera del entrenamiento de un fold (por la agrupacion `StratifiedGroupKFold` sobre `comercio`), el modelo no tiene ninguna fila con esos tokens exactos y debe decidir en base a coincidencias parciales de n-gramas de caracteres (3-5) con comercios de OTRAS categorias, lo que produce el patron observado: comercios completos (95-100% de sus filas) migran en bloque hacia una unica categoria equivocada (ej. `EPS Cuota Moderadora` -> vivienda en 69% de sus filas, `Gas Natural Domiciliario` -> alimentacion en el 100%, `Cuota Hipoteca Vivienda` -> otras en 96%).
2. **`alimentacion` actua como categoria iman para texto no reconocido.** Es la categoria real MENOS frecuente en el OOF (la mas chica de las 8) pero la MAS predicha con amplio margen (mas del doble de veces de las que realmente ocurre), ver tabla de distribucion arriba. Esto sugiere que, ante un comercio sin ningun n-grama reconocible, la funcion de decision calibrada (`CalibratedClassifierCV` sobre `LinearSVC`) tiende a favorecer `alimentacion` como opcion por defecto, probablemente porque en el vocabulario de esa categoria abundan palabras y fragmentos de caracteres cortos y comunes en español (ej. sufijos, numeros, nombres de ciudad que tambien aparecen en las erratas de otros comercios) que generalizan mal como señal discriminativa.
3. **Los pares confundidos no comparten un tema de gasto obvio (salud/vivienda, educacion/ocio, servicios/alimentacion), lo que refuerza la hipotesis 1**: si la confusion fuera por vocabulario semanticamente cercano (dos categorias de gasto parecidas), esperariamos ver pares tematicamente relacionados. En cambio, el patron dominante es "un comercio especifico, no visto, cae entero en una categoria arbitraria", consistente con sobreajuste a nombres de comercio en vez de aprender categorias generalizables.
