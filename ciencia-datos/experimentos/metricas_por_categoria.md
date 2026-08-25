# Metricas por categoria sobre predicciones OOF (out-of-fold)

Calculadas sobre 63,309 predicciones out-of-fold de `ciencia-datos/experimentos/oof_predicciones_cv.csv` (Fase 2: StratifiedGroupKFold(n_splits=5) agrupado por comercio), sin reentrenar nada. `soporte` es el numero de filas reales de esa categoria en el OOF; `tasa_error` es `1 - recall` (proporcion de esa categoria real mal clasificada).

## Metricas

| categoria | precision | recall | f1-score | soporte | tasa de error |
|---|---|---|---|---|---|
| alimentacion | 0.2787 | 0.6639 | 0.3926 | 5,886 | 0.3361 |
| transporte | 0.2832 | 0.3307 | 0.3051 | 5,818 | 0.6693 |
| salud | 0.6606 | 0.3972 | 0.4961 | 8,087 | 0.6028 |
| vivienda | 0.4396 | 0.3786 | 0.4068 | 9,162 | 0.6214 |
| educacion | 0.3861 | 0.3271 | 0.3542 | 5,970 | 0.6729 |
| ocio | 0.6007 | 0.4859 | 0.5372 | 9,280 | 0.5141 |
| servicios | 0.5597 | 0.2365 | 0.3325 | 9,438 | 0.7635 |
| deudas | 0.4044 | 0.8741 | 0.5530 | 3,765 | 0.1259 |
| otras | 0.1350 | 0.1155 | 0.1245 | 5,903 | 0.8845 |
| **macro** | 0.4165 | 0.4233 | 0.3891 | 63,309 | 0.5767 |
| **weighted** | 0.4445 | 0.3977 | 0.3930 | 63,309 | 0.6023 |

## Analisis

- **Categoria mas fuerte:** `deudas` (f1-score 0.5530, precision 0.4044, recall 0.8741, soporte 3,765); es la categoria que el clasificador reconoce con mayor consistencia en comercios no vistos.
- **Categoria mas debil:** `otras` (f1-score 0.1245, precision 0.1350, recall 0.1155, tasa de error 0.8845); es donde el modelo confunde con mayor frecuencia comercios no vistos en entrenamiento.
- **Menor soporte:** `deudas` (3,765 filas reales en el OOF, f1-score 0.5530); al ser la categoria con menos ejemplos, es la candidata mas clara a necesitar mas datos etiquetados antes de sacar conclusiones fuertes sobre su desempeño.

