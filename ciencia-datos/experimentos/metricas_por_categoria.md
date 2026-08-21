# Metricas por categoria sobre predicciones OOF (out-of-fold)

Calculadas sobre 58,894 predicciones out-of-fold de `ciencia-datos/experimentos/oof_predicciones_cv.csv` (Fase 2: StratifiedGroupKFold(n_splits=5) agrupado por comercio), sin reentrenar nada. `soporte` es el numero de filas reales de esa categoria en el OOF; `tasa_error` es `1 - recall` (proporcion de esa categoria real mal clasificada).

## Metricas

| categoria | precision | recall | f1-score | soporte | tasa de error |
|---|---|---|---|---|---|
| alimentacion | 0.2668 | 0.6029 | 0.3699 | 5,721 | 0.3971 |
| transporte | 0.4156 | 0.4764 | 0.4439 | 5,947 | 0.5236 |
| salud | 0.6854 | 0.4738 | 0.5603 | 8,033 | 0.5262 |
| vivienda | 0.4443 | 0.3894 | 0.4150 | 9,084 | 0.6106 |
| educacion | 0.3958 | 0.3022 | 0.3427 | 5,960 | 0.6978 |
| ocio | 0.4937 | 0.4756 | 0.4845 | 9,180 | 0.5244 |
| servicios | 0.7469 | 0.4708 | 0.5776 | 9,229 | 0.5292 |
| otras | 0.1520 | 0.1702 | 0.1606 | 5,740 | 0.8298 |
| **macro** | 0.4501 | 0.4201 | 0.4193 | 58,894 | 0.5799 |
| **weighted** | 0.4788 | 0.4264 | 0.4376 | 58,894 | 0.5736 |

## Analisis

- **Categoria mas fuerte:** `servicios` (f1-score 0.5776, precision 0.7469, recall 0.4708, soporte 9,229); es la categoria que el clasificador reconoce con mayor consistencia en comercios no vistos.
- **Categoria mas debil:** `otras` (f1-score 0.1606, precision 0.1520, recall 0.1702, tasa de error 0.8298); es donde el modelo confunde con mayor frecuencia comercios no vistos en entrenamiento.
- **Menor soporte:** `alimentacion` (5,721 filas reales en el OOF, f1-score 0.3699); al ser la categoria con menos ejemplos, es la candidata mas clara a necesitar mas datos etiquetados antes de sacar conclusiones fuertes sobre su desempeño.

