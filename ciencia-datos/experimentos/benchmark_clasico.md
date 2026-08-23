# Benchmark de modelos clasicos (Fase 9)

Dataset: `C:\Users\HardM\Desktop\Enterprise\hackaton-alura\G9-LATAM-TEAM-44-FinanceAI\ciencia-datos\datos\limpios\transacciones.csv`
Filas entrenables: 58,894 | Comercios unicos: 159
Split: `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)`
agrupado por `comercio`, estratificado por `categoria` (igual que la Fase 2,
`ciencia-datos/scripts/evaluar_cv_agrupada.py`).

## Resultados (ordenados por f1_macro medio, de mejor a peor)

| modelo | accuracy | f1_macro | f1_weighted | balanced_accuracy |
| --- | --- | --- | --- | --- |
| actual (palabra+caracter TFIDF) + LinearSVC calibrado | 0.4276 +/- 0.0733 | 0.4007 +/- 0.0709 | 0.4060 +/- 0.0867 | 0.4362 +/- 0.0567 |
| solo caracter TFIDF (char_wb 3-5) + LinearSVC calibrado | 0.4280 +/- 0.0827 | 0.3934 +/- 0.0626 | 0.4049 +/- 0.0777 | 0.4266 +/- 0.0665 |
| palabra+caracter TFIDF + Naive Bayes (mejor de MultinomialNB/ComplementNB) | 0.4143 +/- 0.0590 | 0.3813 +/- 0.0304 | 0.3803 +/- 0.0451 | 0.4199 +/- 0.0478 |
| palabra+caracter TFIDF + LogisticRegression | 0.4150 +/- 0.0982 | 0.3745 +/- 0.0867 | 0.3796 +/- 0.1082 | 0.4191 +/- 0.0726 |
| solo palabra TFIDF (1,2-gram) + LinearSVC calibrado | 0.2576 +/- 0.0452 | 0.2558 +/- 0.0515 | 0.2464 +/- 0.0600 | 0.2802 +/- 0.0294 |

## Control de reproducibilidad del split

El candidato 1 ("actual") es el mismo pipeline evaluado en la Fase 2
(`ciencia-datos/experimentos/cv_agrupada_comercio.json`). Aqui salio
accuracy = 0.4276 +/- 0.0733,
f1_macro = 0.4007 +/- 0.0709,
f1_weighted = 0.4060 +/- 0.0867,
balanced_accuracy = 0.4362 +/- 0.0567.
Comparar estos numeros contra el JSON de la Fase 2 confirma (o no) que el split
de StratifiedGroupKFold se reprodujo exactamente igual.

## Naive Bayes: MultinomialNB vs ComplementNB

- Naive Bayes: se probaron **MultinomialNB** (f1_macro = 0.3725 +/- 0.0547) y **ComplementNB** (f1_macro = 0.3813 +/- 0.0304). Se eligio **ComplementNB** para la fila del benchmark (descartando MultinomialNB) porque obtuvo el f1_macro medio mas alto de los dos.

## Conclusion

El mejor por f1_macro medio (**actual (palabra+caracter TFIDF) + LinearSVC calibrado**, f1_macro = 0.4007 +/- 0.0709) no se distingue con confianza de: solo caracter TFIDF (char_wb 3-5) + LinearSVC calibrado; palabra+caracter TFIDF + Naive Bayes (mejor de MultinomialNB/ComplementNB); palabra+caracter TFIDF + LogisticRegression. Sus rangos media +/- desviacion estandar de f1_macro se solapan con el del primero, por lo que son estadisticamente equivalentes en este benchmark; la diferencia observada podria deberse a la variabilidad entre folds y no a una ventaja real de un modelo sobre otro.

Recomendacion: mantener el pipeline actual (palabra+caracter TFIDF + LinearSVC
calibrado) salvo que la diferencia frente a otro candidato sea, ademas de
mayor en la media, mayor que la suma de ambas desviaciones estandar (es decir,
una diferencia que no se explique por la variabilidad entre folds). Cuando dos
candidatos son estadisticamente equivalentes en f1_macro, conviene preferir el
mas simple o el mas rapido de entrenar, no el que tenga la cifra ligeramente
mas alta.
