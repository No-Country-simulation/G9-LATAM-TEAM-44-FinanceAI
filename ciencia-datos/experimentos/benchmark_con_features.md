# Benchmark "solo texto" vs. "texto + features adicionales" (Fase 10)

Dataset: `C:\Users\HardM\Desktop\Enterprise\hackaton-alura\G9-LATAM-TEAM-44-FinanceAI\ciencia-datos\datos\limpios\transacciones.csv`
Filas entrenables: 58,894 | Comercios unicos: 159
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
  - `flag_pos`: 10,665 filas (18.11%)
  - `flag_trf`: 10,665 filas (18.11%)
  - `flag_compra`: 823 filas (1.40%)
  - `flag_pago`: 1,095 filas (1.86%)
  - `flag_debito`: 0 filas (0.00%)
  - `flag_credito`: 0 filas (0.00%)
  - `flag_tarj`: 6 filas (0.01%)
- `dia_semana` (0-6) y `mes` (1-12) de la columna "fecha", codificados con
  `OneHotEncoder` (categoricas, no ordinales/ciclicas de verdad).

Todas las numericas se escalan con `StandardScaler`; el texto sigue vectorizado
con TF-IDF palabra (1,2-gram) + caracter (char_wb 3-5), exactamente como en el
pipeline vigente. Se combinan con `sklearn.compose.ColumnTransformer`.

## Resultados (filas nuevas de esta fase, en el orden en que se corrieron)

| modelo | accuracy | f1_macro | f1_weighted | balanced_accuracy |
| --- | --- | --- | --- | --- |
| solo texto (control, igual pipeline vigente/Fase 9) | 0.4276 +/- 0.0733 | 0.4007 +/- 0.0709 | 0.4060 +/- 0.0867 | 0.4362 +/- 0.0567 |
| +monto | 0.4301 +/- 0.0772 | 0.4020 +/- 0.0732 | 0.4075 +/- 0.0893 | 0.4383 +/- 0.0597 |
| +log1p(monto) | 0.4296 +/- 0.0770 | 0.4015 +/- 0.0733 | 0.4070 +/- 0.0893 | 0.4377 +/- 0.0598 |
| +longitud_texto | 0.4229 +/- 0.0884 | 0.3863 +/- 0.0764 | 0.3896 +/- 0.0986 | 0.4309 +/- 0.0624 |
| +flags_prefijos_extracto | 0.4374 +/- 0.0853 | 0.4109 +/- 0.0882 | 0.4118 +/- 0.0990 | 0.4500 +/- 0.0714 |
| +dia_semana+mes | 0.4267 +/- 0.0739 | 0.3996 +/- 0.0719 | 0.4049 +/- 0.0874 | 0.4351 +/- 0.0578 |
| +todas las features (monto: monto) | 0.4276 +/- 0.0897 | 0.3930 +/- 0.0856 | 0.3918 +/- 0.1021 | 0.4412 +/- 0.0684 |

## Control (solo texto)

accuracy = 0.4276 +/- 0.0733,
f1_macro = 0.4007 +/- 0.0709,
f1_weighted = 0.4060 +/- 0.0867,
balanced_accuracy = 0.4362 +/- 0.0567.
(Deberia salir igual o muy cercano al candidato "actual" de la Fase 9 y a la
Fase 2, porque es el mismo pipeline sobre el mismo split.)

## monto vs. log1p(monto)

Entre **monto** (f1_macro = 0.4020 +/- 0.0732) y **log1p(monto)** (f1_macro = 0.4015 +/- 0.0733), se usa **monto** en '+todas las features' porque obtuvo el f1_macro medio mas alto (se descarta log1p(monto) para esa fila combinada).

## Cuanto aporta (o no) cada bloque de features, frente al control de solo texto

- **+monto**: f1_macro = 0.4020 +/- 0.0732 (delta vs. control = +0.0013) -> dentro de 1 desviacion estandar del control (no se distingue con confianza).
- **+log1p(monto)**: f1_macro = 0.4015 +/- 0.0733 (delta vs. control = +0.0008) -> dentro de 1 desviacion estandar del control (no se distingue con confianza).
- **+longitud_texto**: f1_macro = 0.3863 +/- 0.0764 (delta vs. control = -0.0144) -> dentro de 1 desviacion estandar del control (no se distingue con confianza).
- **+flags_prefijos_extracto**: f1_macro = 0.4109 +/- 0.0882 (delta vs. control = +0.0102) -> dentro de 1 desviacion estandar del control (no se distingue con confianza).
- **+dia_semana+mes**: f1_macro = 0.3996 +/- 0.0719 (delta vs. control = -0.0011) -> dentro de 1 desviacion estandar del control (no se distingue con confianza).
- **+todas las features (monto: monto)**: f1_macro = 0.3930 +/- 0.0856 (delta vs. control = -0.0078) -> dentro de 1 desviacion estandar del control (no se distingue con confianza).

## Conclusion

Se consideran equivalentes ("dentro de 1 desviacion estandar") aquellos bloques
cuyo rango media +/- desviacion estandar de f1_macro se solapa con el del control
de solo texto; en ese caso la diferencia observada puede deberse a la variabilidad
entre folds y no a una ventaja real de agregar esa feature. Si ninguna combinacion
(incluida "+todas las features") supera al control fuera de ese margen, la
recomendacion es **mantener el pipeline de solo texto**: es mas simple, mas rapido
de entrenar/servir y evita depender de columnas (monto, fecha, prefijos de extracto)
que pueden no estar disponibles o tener otro formato en produccion.
