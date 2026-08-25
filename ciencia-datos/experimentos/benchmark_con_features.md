# Benchmark "solo texto" vs. "texto + features adicionales" (Fase 10)

Dataset: `C:\Users\Rayle\Desktop\G9-LATAM-TEAM-44-FinanceAI-main\ciencia-datos\datos\limpios\transacciones.csv`
Filas entrenables: 63,309 | Comercios unicos: 170
Split: `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)`
agrupado por `comercio`, estratificado por `categoria` (igual que las Fases 2 y 9).

Base: el pipeline vigente (palabra+caracter TFIDF + `LinearSVC` calibrado), que
en la Fase 9 no fue superado con confianza por ningun otro vectorizador/clasificador
clasico (ver `ciencia-datos/experimentos/benchmark_clasico.md`). Esta fase parte de
ese mismo pipeline y le agrega bloques de features numericas/categoricas via
`ColumnTransformer`, sin usar nada derivado de la categoria real.

## Features probadas

- `monto` y `log1p(monto)` (columna "monto", siempre > 0 en este dataset).
- `longitud_texto` = `len(descripcion_limpia)`.
- flags binarios `flag_<token>` para pos, trf, compra, pago, debito, credito, tarj, buscados en la
  columna **"descripcion" original** (sin limpiar), porque `normalizar_texto()`
  los quita a proposito al construir `descripcion_limpia`.
  Frecuencia de cada flag en el conjunto entrenable:
  - `flag_pos`: 11,453 filas (18.09%)
  - `flag_trf`: 11,453 filas (18.09%)
  - `flag_compra`: 837 filas (1.32%)
  - `flag_pago`: 2,669 filas (4.22%)
  - `flag_debito`: 0 filas (0.00%)
  - `flag_credito`: 1,729 filas (2.73%)
  - `flag_tarj`: 8 filas (0.01%)
- `dia_semana` (0-6) y `mes` (1-12) de la columna "fecha", codificados con
  `OneHotEncoder` (categoricas, no ordinales/ciclicas de verdad).

Todas las numericas se escalan con `StandardScaler`; el texto sigue vectorizado
con TF-IDF palabra (1,2-gram) + caracter (char_wb 3-5), exactamente como en el
pipeline vigente. Se combinan con `sklearn.compose.ColumnTransformer`.

## Resultados (filas nuevas de esta fase, en el orden en que se corrieron)

| modelo | accuracy | f1_macro | f1_weighted | balanced_accuracy |
| --- | --- | --- | --- | --- |
| solo texto (control, igual pipeline vigente/Fase 9) | 0.4000 +/- 0.1149 | 0.3837 +/- 0.0987 | 0.3658 +/- 0.1119 | 0.4323 +/- 0.0947 |
| +monto | 0.4018 +/- 0.1126 | 0.3847 +/- 0.0962 | 0.3681 +/- 0.1093 | 0.4324 +/- 0.0920 |
| +log1p(monto) | 0.4006 +/- 0.1146 | 0.3842 +/- 0.0983 | 0.3666 +/- 0.1115 | 0.4324 +/- 0.0942 |
| +longitud_texto | 0.4178 +/- 0.0862 | 0.3962 +/- 0.0810 | 0.3749 +/- 0.0800 | 0.4535 +/- 0.0783 |
| +flags_prefijos_extracto | 0.4071 +/- 0.1107 | 0.3863 +/- 0.0938 | 0.3621 +/- 0.1036 | 0.4513 +/- 0.0958 |
| +dia_semana+mes | 0.4003 +/- 0.1135 | 0.3836 +/- 0.0974 | 0.3660 +/- 0.1104 | 0.4322 +/- 0.0936 |
| +todas las features (monto: monto) | 0.4227 +/- 0.0984 | 0.3983 +/- 0.0873 | 0.3739 +/- 0.0941 | 0.4690 +/- 0.0833 |

## Control (solo texto)

accuracy = 0.4000 +/- 0.1149,
f1_macro = 0.3837 +/- 0.0987,
f1_weighted = 0.3658 +/- 0.1119,
balanced_accuracy = 0.4323 +/- 0.0947.
(Deberia salir igual o muy cercano al candidato "actual" de la Fase 9 y a la
Fase 2, porque es el mismo pipeline sobre el mismo split.)

## monto vs. log1p(monto)

Entre **monto** (f1_macro = 0.3847 +/- 0.0962) y **log1p(monto)** (f1_macro = 0.3842 +/- 0.0983), se usa **monto** en '+todas las features' porque obtuvo el f1_macro medio mas alto (se descarta log1p(monto) para esa fila combinada).

## Cuanto aporta (o no) cada bloque de features, frente al control de solo texto

- **+monto**: f1_macro = 0.3847 +/- 0.0962 (delta vs. control = +0.0010) -> dentro de 1 desviacion estandar del control (no se distingue con confianza).
- **+log1p(monto)**: f1_macro = 0.3842 +/- 0.0983 (delta vs. control = +0.0004) -> dentro de 1 desviacion estandar del control (no se distingue con confianza).
- **+longitud_texto**: f1_macro = 0.3962 +/- 0.0810 (delta vs. control = +0.0125) -> dentro de 1 desviacion estandar del control (no se distingue con confianza).
- **+flags_prefijos_extracto**: f1_macro = 0.3863 +/- 0.0938 (delta vs. control = +0.0025) -> dentro de 1 desviacion estandar del control (no se distingue con confianza).
- **+dia_semana+mes**: f1_macro = 0.3836 +/- 0.0974 (delta vs. control = -0.0001) -> dentro de 1 desviacion estandar del control (no se distingue con confianza).
- **+todas las features (monto: monto)**: f1_macro = 0.3983 +/- 0.0873 (delta vs. control = +0.0146) -> dentro de 1 desviacion estandar del control (no se distingue con confianza).

## Conclusion

Se consideran equivalentes ("dentro de 1 desviacion estandar") aquellos bloques
cuyo rango media +/- desviacion estandar de f1_macro se solapa con el del control
de solo texto; en ese caso la diferencia observada puede deberse a la variabilidad
entre folds y no a una ventaja real de agregar esa feature. Si ninguna combinacion
(incluida "+todas las features") supera al control fuera de ese margen, la
recomendacion es **mantener el pipeline de solo texto**: es mas simple, mas rapido
de entrenar/servir y evita depender de columnas (monto, fecha, prefijos de extracto)
que pueden no estar disponibles o tener otro formato en produccion.
