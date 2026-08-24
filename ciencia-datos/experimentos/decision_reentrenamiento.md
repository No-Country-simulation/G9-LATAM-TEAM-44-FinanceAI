# Decision de reentrenamiento (Fase 14)

## 1. Resumen honesto de la evidencia disponible

Esta fase no corre experimentos nuevos: consolida lo que ya produjeron las
Fases 9, 10 y 11 para decidir si hay evidencia suficiente para reemplazar
`ciencia-datos/artefactos/clasificador_gastos.joblib`.

### Fase 9 - Benchmark de modelos clasicos (`benchmark_clasico.md`)

Sobre el mismo split (`StratifiedGroupKFold(n_splits=5, shuffle=True,
random_state=42)`, agrupado por `comercio`, 58,894 filas entrenables, 159
comercios unicos) se compararon 5 combinaciones de vectorizador/clasificador.
El pipeline vigente (palabra+caracter TFIDF + `LinearSVC` calibrado) obtuvo
f1_macro = 0.4007 +/- 0.0709. Los otros 4 candidatos:

| candidato | f1_macro |
| --- | --- |
| solo caracter TFIDF (char_wb 3-5) + LinearSVC calibrado | 0.3934 +/- 0.0626 |
| palabra+caracter TFIDF + Naive Bayes (ComplementNB) | 0.3813 +/- 0.0304 |
| palabra+caracter TFIDF + LogisticRegression | 0.3745 +/- 0.0867 |
| solo palabra TFIDF (1,2-gram) + LinearSVC calibrado | 0.2558 +/- 0.0515 |

Ninguno supera al pipeline vigente; los tres primeros quedan dentro de 1
desviacion estandar del control (diferencia explicable por variabilidad entre
folds, no por una ventaja real del modelo), y el cuarto es claramente peor.

### Fase 10 - Features adicionales (`benchmark_con_features.md`)

Sobre el mismo split y el mismo pipeline base, se agregaron bloques de
features numericas/categoricas (`monto`, `log1p(monto)`, `longitud_texto`,
flags de prefijos de extracto, `dia_semana`+`mes`) via `ColumnTransformer`.
Control (solo texto): f1_macro = 0.4007 +/- 0.0709.

| bloque agregado | f1_macro | delta vs. control |
| --- | --- | --- |
| +monto | 0.4020 +/- 0.0732 | +0.0013 |
| +log1p(monto) | 0.4015 +/- 0.0733 | +0.0008 |
| +longitud_texto | 0.3863 +/- 0.0764 | -0.0144 |
| +flags_prefijos_extracto | 0.4109 +/- 0.0882 | +0.0102 |
| +dia_semana+mes | 0.3996 +/- 0.0719 | -0.0011 |
| +todas las features (monto: monto) | 0.3930 +/- 0.0856 | -0.0078 |

Los 6 deltas caen dentro de 1 desviacion estandar del control. Ninguna
combinacion de features, incluida "+todas las features", supera al control
fuera del margen de ruido entre folds.

### Fase 11 - Analisis manual de errores (`analisis_errores.md`)

Sobre una muestra estratificada de 72 errores (de 33,780 errores totales sobre
las 58,894 filas entrenables evaluadas OOF en la CV agrupada por comercio de
la Fase 2), la causa dominante es:

| causa_probable | n en la muestra | % de la muestra |
| --- | --- | --- |
| comercio_desconocido_en_vocabulario | 55 | 76.4% |
| categoria_ambigua | 13 | 18.1% |
| texto_insuficiente | 2 | 2.8% |
| keyword_compartido_entre_categorias | 2 | 2.8% |
| posible_error_de_etiqueta | 0 | 0.0% |

Ademas, se verifico sobre las 58,894 filas entrenables completas que el 100%
de los 159 comercios (159/159) tiene una unica categoria en el 100% de sus
transacciones: no hay evidencia de etiquetas inconsistentes en el dataset.
El problema de fondo no es de algoritmo ni de etiquetado, es de **falta de
diversidad real de comercios** en el dataset sintetico (159 comercios): la
mayoria de los errores ocurre cuando el comercio evaluado nunca aparecio en
el vocabulario de entrenamiento (consistente con el diseno de CV agrupada por
comercio de la Fase 2).

### Conclusion de la evidencia

Cruzando las tres fases: ningun candidato de vectorizador/clasificador
(Fase 9) ni ninguna combinacion de features adicionales (Fase 10) supera al
pipeline vigente (palabra+caracter TFIDF + `LinearSVC` calibrado, f1_macro
~0.4007 +/- 0.0709 en comercios no vistos) fuera del margen de ruido entre
folds. El analisis de errores (Fase 11) explica por que: el 76.4% de los
errores muestreados son por comercio desconocido en vocabulario, es decir,
un limite de cobertura del dataset, no algo que un cambio de algoritmo o de
features pueda resolver.

## 2. Decision explicita

**No se reemplaza `ciencia-datos/artefactos/clasificador_gastos.joblib` ni se
sube la version en `ciencia-datos/artefactos/metadatos.json`** (se mantiene en
`1.0.0`, entrenado el `2026-08-17T17:49:00`, con
`clasificador_comercios_no_vistos.f1_macro = 0.4181` /
`accuracy = 0.4111` segun el metadato vigente).

Justificacion: no hay ningun candidato evaluado (Fase 9) ni ninguna
combinacion de features (Fase 10) que supere al pipeline actual fuera del
margen de ruido entre folds (diferencias siempre dentro de 1 desviacion
estandar del control, o peores). Reentrenar ahora con cualquiera de estos
candidatos seria **cosmetico**: cambiaria el numero de version y la fecha de
`metadatos.json` sin una mejora real y defendible en f1_macro sobre comercios
no vistos. El roadmap pide evidencia de mejora, no un numero de version mas
alto por si solo. Esta decision es consistente con las recomendaciones
explicitas de cierre de las Fases 9 y 10 (mantener el pipeline vigente).

Esta fase, por lo tanto, **no modifica** ningun archivo bajo
`ciencia-datos/artefactos/` (verificado con `git diff` antes de commitear,
ver seccion 4).

## 3. Que si moveria la aguja (proximo paso recomendado, pendiente)

Segun la Fase 11, el 76.4% de los errores muestreados vienen de
`comercio_desconocido_en_vocabulario`. Lo que moveria la aguja de f1_macro en
comercios no vistos no es mas tuning del algoritmo actual (ya descartado por
las Fases 9 y 10), sino **diversificar los comercios reales del dataset**:
sumar comercios (y variantes de nombre) adicionales por categoria a partir de
una fuente externa real, por ejemplo Foursquare Places (u otra fuente
equivalente de nombres de comercios por categoria), para que el vectorizador
vea vocabulario compartido mas alla de los 159 comercios sinteticos actuales.

Este paso queda **explicitamente pendiente**: en un intento anterior del
roadmap, la integracion de un dataset externo de comercios reales (Foursquare
en Hugging Face) no se pudo completar porque el dataset requiere una cuenta
"gated" en Hugging Face. No se dispone todavia de un dataset externo de
comercios reales integrado a este proyecto.

## 4. Verificacion de que no se tocaron artefactos del modelo

Antes de commitear esta fase se corrio `git diff --stat` sobre el working
tree y se confirmo que los unicos cambios son la creacion de este archivo
(`ciencia-datos/experimentos/decision_reentrenamiento.md`); no hay cambios en
`ciencia-datos/artefactos/clasificador_gastos.joblib` ni en
`ciencia-datos/artefactos/metadatos.json`.
