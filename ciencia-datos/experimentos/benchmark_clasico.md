# Benchmark de modelos clasicos (Fase 9)

Dataset: `C:\Users\Rayle\Desktop\G9-LATAM-TEAM-44-FinanceAI-main\ciencia-datos\datos\limpios\transacciones.csv`
Filas entrenables: 63,309 | Comercios unicos: 170
Split: `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)`
agrupado por `comercio`, estratificado por `categoria` (igual que la Fase 2,
`ciencia-datos/scripts/evaluar_cv_agrupada.py`).

## Resultados (ordenados por f1_macro medio, de mejor a peor)

| modelo | accuracy | f1_macro | f1_weighted | balanced_accuracy |
| --- | --- | --- | --- | --- |
| palabra+caracter TFIDF + Naive Bayes (mejor de MultinomialNB/ComplementNB) | 0.4238 +/- 0.0828 | 0.4087 +/- 0.0595 | 0.3917 +/- 0.0713 | 0.4450 +/- 0.0689 |
| solo caracter TFIDF (char_wb 3-5) + LinearSVC calibrado | 0.4173 +/- 0.0922 | 0.3894 +/- 0.0823 | 0.3776 +/- 0.0919 | 0.4386 +/- 0.0711 |
| actual (palabra+caracter TFIDF) + LinearSVC calibrado | 0.4000 +/- 0.1149 | 0.3837 +/- 0.0987 | 0.3658 +/- 0.1119 | 0.4323 +/- 0.0947 |
| palabra+caracter TFIDF + LogisticRegression | 0.3965 +/- 0.0950 | 0.3729 +/- 0.0820 | 0.3519 +/- 0.0873 | 0.4282 +/- 0.0783 |
| solo palabra TFIDF (1,2-gram) + LinearSVC calibrado | 0.2605 +/- 0.0724 | 0.2549 +/- 0.0823 | 0.2193 +/- 0.0800 | 0.3148 +/- 0.0798 |

## Control de reproducibilidad del split

El candidato 1 ("actual") es el mismo pipeline evaluado en la Fase 2
(`ciencia-datos/experimentos/cv_agrupada_comercio.json`). Aqui salio
accuracy = 0.4000 +/- 0.1149,
f1_macro = 0.3837 +/- 0.0987,
f1_weighted = 0.3658 +/- 0.1119,
balanced_accuracy = 0.4323 +/- 0.0947.
Comparar estos numeros contra el JSON de la Fase 2 confirma (o no) que el split
de StratifiedGroupKFold se reprodujo exactamente igual.

## Naive Bayes: MultinomialNB vs ComplementNB

- Naive Bayes: se probaron **MultinomialNB** (f1_macro = 0.3819 +/- 0.0758) y **ComplementNB** (f1_macro = 0.4087 +/- 0.0595). Se eligio **ComplementNB** para la fila del benchmark (descartando MultinomialNB) porque obtuvo el f1_macro medio mas alto de los dos.

## Conclusion

El mejor por f1_macro medio (**palabra+caracter TFIDF + Naive Bayes (mejor de MultinomialNB/ComplementNB)**, f1_macro = 0.4087 +/- 0.0595) no se distingue con confianza de: solo caracter TFIDF (char_wb 3-5) + LinearSVC calibrado; actual (palabra+caracter TFIDF) + LinearSVC calibrado; palabra+caracter TFIDF + LogisticRegression. Sus rangos media +/- desviacion estandar de f1_macro se solapan con el del primero, por lo que son estadisticamente equivalentes en este benchmark; la diferencia observada podria deberse a la variabilidad entre folds y no a una ventaja real de un modelo sobre otro.

Recomendacion: mantener el pipeline actual (palabra+caracter TFIDF + LinearSVC
calibrado) salvo que la diferencia frente a otro candidato sea, ademas de
mayor en la media, mayor que la suma de ambas desviaciones estandar (es decir,
una diferencia que no se explique por la variabilidad entre folds). Cuando dos
candidatos son estadisticamente equivalentes en f1_macro, conviene preferir el
mas simple o el mas rapido de entrenar, no el que tenga la cifra ligeramente
mas alta.
