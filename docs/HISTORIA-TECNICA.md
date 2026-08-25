# Historia tecnica del clasificador de gastos de FinanceAI

Este documento cuenta, en orden cronologico y con las cifras exactas de cada
experimento, como llegamos al pipeline de clasificacion de gastos que esta en
produccion hoy (`palabra+caracter TFIDF + LinearSVC calibrado`). No es una
narrativa de marketing: es el registro honesto de un modelo que parecia
perfecto, dejo de parecerlo en cuanto lo evaluamos bien, y cuya limitacion
real resulto ser el dataset, no el algoritmo. Cada cifra citada sale de un
archivo real bajo `ciencia-datos/experimentos/` o de `ciencia-datos/notebook.ipynb`;
ninguna es de memoria.

> **Nota de lectura.** Las secciones 1 a 9 describen el clasificador de **ocho**
> categorias, que es el que existia mientras se hicieron esos experimentos. En
> agosto de 2026 se anadio una novena, `deudas`, y se regeneraron el dataset y
> todos los archivos de `experimentos/`. Las cifras de esas secciones ya no
> coinciden con los archivos que estan hoy en el repositorio: se conservan como
> registro de lo que se midio entonces, porque el razonamiento que justifica el
> pipeline actual salio de ahi. Las cifras vigentes estan en la seccion 10.

## 1. El primer numero: accuracy 0.9999 (particion aleatoria)

La primera evaluacion del clasificador de gastos se hizo con una particion
aleatoria train/test (80/20) sobre las 58,894 filas entrenables del dataset
limpio (`transacciones.csv`, 159 comercios unicos). El resultado, registrado
en `ciencia-datos/experimentos/baseline_v1.json` (bloque `particion_aleatoria`):

- `accuracy` = 0.9999320837
- `f1_macro` = 0.9999292221
- `f1_weighted` = 0.9999320881
- `balanced_accuracy` = 0.9999455338
- 44,170 filas de entrenamiento, 14,724 de prueba, 12.62 segundos de entrenamiento.

Un modelo que clasifica correctamente el 99.99% de las transacciones parece,
a primera vista, un exito rotundo. No lo es, y la siguiente seccion explica
por que.

## 2. Se detecta la fuga: el modelo memoriza nombres de comercio

El propio notebook (`ciencia-datos/notebook.ipynb`, seccion 10.2 "Particion
por comercio (comercios nunca vistos)") documenta el diagnostico correcto de
ese 0.9999: en este dataset, **cada comercio pertenece a una unica categoria**
en el 100% de sus transacciones. La celda de markdown que acompaña a la
particion aleatoria (seccion 10.1) lo dice explicitamente:

> "Practicamente perfecto, y conviene explicar por que: en el dataset cada
> comercio pertenece a una unica categoria, asi que memorizar el nombre
> basta. Esta metrica no predice el rendimiento en produccion."

Con una particion aleatoria, casi todos los comercios del conjunto de prueba
ya aparecieron en el conjunto de entrenamiento (con otras transacciones del
mismo comercio). El vectorizador TF-IDF (palabra + caracter) no necesita
aprender nada sobre "que hace" cada categoria de gasto: le basta reconocer el
nombre del comercio, palabra por palabra o caracter por caracter, para acertar
la categoria que ese comercio siempre tuvo. El 0.9999 mide memorizacion de
nombres, no capacidad de generalizar a comercios nuevos, que es exactamente lo
que el modelo enfrentara en produccion cuando un usuario registre un gasto en
un comercio que el dataset de entrenamiento nunca vio.

Esto motivo la pregunta que el propio notebook plantea a continuacion: "?que
pasa si evaluamos sobre comercios que el modelo nunca vio?".

## 3. Evaluacion honesta: comercio no visto

### 3.1 Primera senal: particion por comercio (~0.41)

La seccion 10.2 del notebook responde a esa pregunta reservando un grupo de
comercios completo para prueba (ningun comercio aparece a la vez en train y
test). El resultado, tambien en `baseline_v1.json` (bloque
`particion_por_comercio`, sobre 159 comercios totales, 40 reservados para
prueba):

- `accuracy` = 0.4124769136
- `f1_macro` = 0.4189176117
- `f1_weighted` = 0.4146979700
- `balanced_accuracy` = 0.4389476409
- 44,275 filas de entrenamiento, 14,619 de prueba.

La caida es enorme: de 0.9999 a ~0.41. Como dice el notebook, "la caida es
grande y es el resultado mas informativo del notebook". Este es el numero que
de verdad importa para produccion: que tan bien clasifica el modelo un
comercio que jamas vio en entrenamiento, que es la situacion real de un
usuario nuevo o de un comercio poco comun.

### 3.2 Confirmacion con CV agrupada 5-fold (~0.4276 +/- 0.0733)

Una sola particion train/test por comercio puede ser optimista o pesimista
segun que comercios caen del lado de prueba. Para obtener una estimacion mas
robusta, la Fase 2 del roadmap corrio una validacion cruzada agrupada por
comercio (`StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)`,
estratificada por categoria) sobre las mismas 58,894 filas y 159 comercios.
El resumen, en `ciencia-datos/experimentos/cv_agrupada_comercio.json`
(bloque `resumen_metricas`):

- `accuracy`: media 0.4276220666, desviacion estandar 0.0732627379
- `f1_macro`: media 0.4007172232, desviacion estandar 0.0708905210
- `f1_weighted`: media 0.4059531645, desviacion estandar 0.0866960306
- `balanced_accuracy`: media 0.4362178765, desviacion estandar 0.0566812496

Esto confirma el ~0.41 de la particion unica: el pipeline vigente generaliza a
comercios no vistos con un accuracy medio de ~0.4276, no ~0.9999. Pero el dato
igual de importante es la **desviacion estandar de 0.0733 en accuracy**: entre
los 5 folds, el accuracy individual oscila desde 0.3201 (fold 0) hasta 0.5425
(fold 3) -- ver `resultados_por_fold` en el mismo JSON. Con solo 159 comercios
unicos repartidos en 5 folds (entre 126 y 129 comercios de entrenamiento y
entre 30 y 33 de prueba por fold), que unos pocos comercios "dificiles" caigan
en un fold u otro cambia el resultado de forma importante. Esa alta varianza
entre folds es, en si misma, una senal de que el dataset tiene pocos comercios
para estimar con precision el desempeño en comercio no visto.

## 4. Donde falla y donde no: matriz de confusion OOD y metricas por categoria

Con las 58,894 predicciones out-of-fold de la CV agrupada (cada prediccion
hecha por un modelo que nunca vio ese comercio), se construyeron una matriz de
confusion y metricas por categoria para entender el patron de error, no solo
su magnitud.

### 4.1 Metricas por categoria (`metricas_por_categoria.md`)

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

`servicios` es la categoria mas fuerte (f1-score 0.5776, precision 0.7469).
`otras` es la mas debil por lejos (f1-score 0.1606, tasa de error 0.8298): es
un cajon de sastre sin vocabulario propio compartido entre sus comercios, tal
como anticipa la seccion 10.2 del notebook.

### 4.2 Matriz de confusion OOD (`matriz_confusion_ood.md`)

Accuracy global sobre el OOF: 0.4264 (consistente con el 0.4276 de la CV, la
pequeña diferencia es porque este numero pondera cada fila igual en vez de
promediar accuracy por fold). Las confusiones dominantes, ordenadas por
proporcion de la fila real:

| real | predicha | casos | % de la fila real |
|---|---|---|---|
| otras | alimentacion | 2,293 | 39.9477% |
| salud | vivienda | 2,363 | 29.4162% |
| educacion | ocio | 1,464 | 24.5638% |
| vivienda | otras | 2,023 | 22.2699% |
| ocio | alimentacion | 1,925 | 20.9695% |

El analisis del propio archivo identifica el mecanismo: comercios completos
(no una fraccion de sus transacciones) migran en bloque hacia una categoria
equivocada cuando el modelo nunca los vio en entrenamiento. Ejemplos citados:
`Gas Natural Domiciliario` cae en `alimentacion` en el 100.0000% de sus filas
del OOF; `Cuota Hipoteca Vivienda` cae en `otras` en el 96.0429%;
`Suscripcion Platzi` cae en `ocio` en el 99.8054%. Ademas, `alimentacion` es
la categoria real menos frecuente del OOF (5,721 filas) pero la mas predicha
con amplio margen (12,926 filas, razon predichas/reales = 2.2594): actua como
"iman" por defecto cuando el modelo no reconoce ningun n-grama del comercio.

## 5. Calibracion: predict_proba no es una probabilidad real en OOD

Si el modelo va a usar su propia confianza para decidir cuando abstenerse,
esa confianza tiene que significar algo. La Fase 5
(`ciencia-datos/experimentos/calibracion.json`) evaluo la calibracion de
`predict_proba` sobre las mismas 58,894 predicciones out-of-fold:

- **Expected Calibration Error (ECE)**: 0.3335 (`0.33351917945890486`)
- **Brier score multiclase**: 0.1152 (`0.1152393999304468`)

La curva de confiabilidad (10 bins) muestra por que: en el bin de mayor
confianza (0.9-1.0, que concentra 27,306 de las 58,894 filas), la confianza
media declarada es 0.9772 pero la accuracy observada es solo 0.5670. En
varios bins intermedios la relacion ni siquiera es monotona (ej. bin 0.7-0.8
tiene confianza media 0.7465 pero accuracy observada de solo 0.2577, mas baja
que bins de confianza menor). Esto confirma que **`predict_proba` no es una
probabilidad calibrada en comercios no vistos**: es, en el mejor de los casos,
un score util para ordenar relativamente que tan seguro esta el modelo (mas
confianza, en general, mejor accuracy agregada -- ver la tabla de
`coverage_vs_accuracy` mas abajo), pero no se puede leer como "la probabilidad
real de que esta prediccion sea correcta es X%".

La misma Fase 5 midio la relacion cobertura/accuracy que si es util
operativamente (`coverage_vs_accuracy` en `calibracion.json`):

| umbral | cobertura | accuracy sobre lo aceptado |
|---|---|---|
| 0.0 (sin filtro) | 1.0000 | 0.4264 |
| 0.5 | 0.8182 | 0.4524 |
| 0.7 | 0.5888 | 0.5016 |
| 0.8 | 0.5427 | 0.5223 |
| 0.9 | 0.4636 | 0.5670 |

Subir el umbral de confianza si sube la accuracy de lo que se acepta, a costa
de cobertura -- es una herramienta de abstencion valida, aunque el numero de
confianza en si no sea una probabilidad calibrada.

## 6. Benchmark de 5 modelos clasicos y de features adicionales: el algoritmo no es el cuello de botella

### 6.1 Cinco combinaciones de vectorizador/clasificador (Fase 9, `benchmark_clasico.md`)

Sobre el mismo split (`StratifiedGroupKFold`, 5 folds, agrupado por
comercio), se compararon 5 combinaciones:

| modelo | f1_macro |
| --- | --- |
| actual (palabra+caracter TFIDF) + LinearSVC calibrado | 0.4007 +/- 0.0709 |
| solo caracter TFIDF (char_wb 3-5) + LinearSVC calibrado | 0.3934 +/- 0.0626 |
| palabra+caracter TFIDF + Naive Bayes (ComplementNB) | 0.3813 +/- 0.0304 |
| palabra+caracter TFIDF + LogisticRegression | 0.3745 +/- 0.0867 |
| solo palabra TFIDF (1,2-gram) + LinearSVC calibrado | 0.2558 +/- 0.0515 |

El pipeline vigente encabeza la tabla, pero los tres siguientes candidatos
quedan dentro de 1 desviacion estandar del control: **la diferencia se
explica por variabilidad entre folds, no por una ventaja real de un modelo
sobre otro**. Solo el candidato "solo palabra TFIDF" es claramente peor.

### 6.2 Features numericas/categoricas adicionales (Fase 10, `benchmark_con_features.md`)

Agregando `monto`, `log1p(monto)`, `longitud_texto`, flags de prefijos de
extracto (pos/trf/compra/pago) y `dia_semana`+`mes` via `ColumnTransformer`,
sobre el mismo control (f1_macro = 0.4007 +/- 0.0709):

| bloque agregado | f1_macro | delta vs. control |
| --- | --- | --- |
| +monto | 0.4020 +/- 0.0732 | +0.0013 |
| +log1p(monto) | 0.4015 +/- 0.0733 | +0.0008 |
| +longitud_texto | 0.3863 +/- 0.0764 | -0.0144 |
| +flags_prefijos_extracto | 0.4109 +/- 0.0882 | +0.0102 |
| +dia_semana+mes | 0.3996 +/- 0.0719 | -0.0011 |
| +todas las features (monto: monto) | 0.3930 +/- 0.0856 | -0.0078 |

Los 6 deltas caen dentro de 1 desviacion estandar del control. Ninguna
combinacion, ni siquiera "+todas las features" junta, supera al pipeline de
solo texto fuera del margen de ruido entre folds.

**Conclusion de ambas fases: ni cambiar de algoritmo (Fase 9) ni agregar
features adicionales al texto (Fase 10) mejora de forma estadisticamente
defendible el f1_macro en comercio no visto.** El cuello de botella no esta
en el algoritmo ni en que columnas se usan como input.

## 7. Analisis de 72 errores: el cuello de botella es la diversidad de comercios

La Fase 11 (`analisis_errores.md`) tomo una muestra estratificada de 72
errores (de 33,780 errores totales sobre las 58,894 filas entrenables
evaluadas OOF) y clasifico manualmente la causa probable de cada uno:

| causa_probable | n en la muestra | % de la muestra |
|---|---|---|
| comercio_desconocido_en_vocabulario | 55 | 76.4% |
| categoria_ambigua | 13 | 18.1% |
| texto_insuficiente | 2 | 2.8% |
| keyword_compartido_entre_categorias | 2 | 2.8% |
| posible_error_de_etiqueta | 0 | 0.0% |

El 76.4% de los errores muestreados ocurren cuando el comercio evaluado nunca
aparecio en el vocabulario de entrenamiento (consistente con el diseno de CV
agrupada por comercio). Ademas, se verifico sobre las 58,894 filas completas
que el 100% de los 159 comercios (159/159) declara una unica categoria en el
100% de sus transacciones: no hay evidencia de etiquetas inconsistentes en el
dataset (por eso `posible_error_de_etiqueta` tiene 0 casos en la muestra). El
problema de fondo no es de algoritmo ni de datos mal etiquetados: es **falta
de diversidad real de comercios** en un dataset sintetico de solo 159
comercios.

## 8. Decision: no reentrenar todavia

Cruzando la evidencia de las Fases 9, 10 y 11, la Fase 14
(`decision_reentrenamiento.md`) tomo una decision explicita: **no se
reemplaza** `ciencia-datos/artefactos/clasificador_gastos.joblib` ni se sube
la version en `ciencia-datos/artefactos/metadatos.json` (se mantiene en
`1.0.0`, entrenado el `2026-08-17T17:49:00`, con
`clasificador_comercios_no_vistos.f1_macro = 0.4181` /
`accuracy = 0.4111` segun el metadato vigente).

La justificacion es la misma que ya se vio en las secciones 6 y 7: ningun
candidato de vectorizador/clasificador ni ninguna combinacion de features
supera al pipeline vigente fuera del margen de ruido entre folds, y el
analisis de errores explica por que (76.4% de los errores son por comercio
desconocido en vocabulario). Reentrenar ahora con cualquiera de esos
candidatos seria **cosmetico**: cambiaria el numero de version y la fecha del
metadato sin una mejora real y defendible en f1_macro sobre comercio no
visto.

El proximo paso real, segun la misma Fase 14, es **diversificar los comercios
del dataset** con una fuente externa de nombres de comercio reales por
categoria (por ejemplo Foursquare Places u otra equivalente), para que el
vectorizador vea vocabulario compartido mas alla de los 159 comercios
sinteticos actuales. Este paso queda **explicitamente pendiente**: un intento
anterior de integrar el dataset de Foursquare en Hugging Face no se pudo
completar porque ese dataset requiere una cuenta "gated" en Hugging Face. Hoy
no hay ningun dataset externo de comercios reales integrado al proyecto.

## 9. Mientras tanto: estrategia de abstencion (Fase 12)

Mientras no exista ese dataset externo, la Fase 12 implemento una mitigacion
operativa que no depende de mejorar el modelo: exponer un **estado de
confianza explicito** (`estado_confianza`: "aceptado" | "requiere_revision" |
"otras") ademas de la categoria y la confianza numerica, tanto en
`POST /clasificar` (`srv-python`) como en el detalle de `ClassificationService`
(`srv-java`). Los cortes, tomados directamente de la tabla
`coverage_vs_accuracy` de `calibracion.json` (Fase 5, seccion 5 de este
documento):

- **aceptado**: confianza >= 0.8 -> accuracy sobre lo aceptado 0.5223
  (31,959 de 58,894 filas, cobertura 0.5427) vs. accuracy global OOD 0.4264
  (+22.5% relativo).
- **requiere_revision**: 0.5 <= confianza < 0.8 -> accuracy en el corte 0.5
  es 0.4524 (48,187 de 58,894 filas).
- **otras**: confianza < 0.5, sin cambio de comportamiento respecto al umbral
  ya vigente.

Esta funcionalidad es aditiva: no toca el `umbral_confianza=0.5` que ya
existia, y se probo con 14 casos nuevos en
`srv-python/tests/test_estado_confianza.py` y 4 casos adicionales en
`ClassificationServiceTest` (uno por estado, mas el modo degradado del
`FallbackClassifier`). Es la respuesta honesta a lo que muestran las
secciones 3 a 7: mientras el dataset no tenga mas diversidad real de
comercios, la forma responsable de usar el modelo no es fingir una precision
que no tiene, sino decirle al usuario (o al sistema que consume la API)
cuando la prediccion es confiable y cuando conviene revisarla a mano.

## 10. Novena categoria: `deudas` (agosto de 2026)

Los pagos de tarjeta de credito y las cuotas de credito caian en `otras` con
confianza mediocre, y por el camino se descubrio que el normalizador borraba la
palabra `credito` junto con los prefijos de extracto: `PAGO TARJETA DE CREDITO`
se quedaba en `tarjeta de`. Se anadio `deudas` como novena categoria, se saco
`credito` de la lista de ruido y se regenero el dataset con 3,909 pagos de deuda
(antes 872, demasiado pocos para aprender la clase).

El resultado no fue el esperado. `deudas` no solo se aprende: es **la categoria
mas robusta de las nueve** ante comercios no vistos.

| categoria | f1-score OOD | soporte |
|---|---|---|
| deudas | **0.5530** | 3,765 |
| ocio | 0.5372 | 9,280 |
| salud | 0.4961 | 8,087 |
| vivienda | 0.4068 | 9,162 |
| alimentacion | 0.3926 | 5,886 |
| educacion | 0.3542 | 5,970 |
| servicios | 0.3325 | 9,438 |
| transporte | 0.3051 | 5,818 |
| otras | 0.1245 | 5,903 |

Tiene explicacion, y encaja con lo que dice la seccion 7. El cuello de botella
del modelo es que los nombres de comercio son arbitrarios: *Exito*, *Jumbo* y
*Ara* no comparten nada mas que el contexto. Los pagos de deuda no funcionan
asi: *tarjeta*, *credito*, *cuota* y *prestamo* son vocabulario descriptivo, no
marcas. El modelo generaliza bien justo donde el texto describe la operacion en
vez de nombrar a un tercero.

De paso subio la evaluacion honesta del clasificador: accuracy por comercio no
visto de 0.4125 a **0.4675**, f1_macro de la CV agrupada a 0.3837 +/- 0.0987.

Una nota sobre la eleccion del algoritmo: en este dataset el benchmark pone a
Naive Bayes por delante del modelo vigente (f1_macro 0.4087 vs. 0.3837). La
diferencia esta dentro de una desviacion estandar (+/-0.0595 y +/-0.0987), asi
que no se distingue del ruido y no se cambio nada, igual que en la seccion 6.
Merece una comprobacion con mas semillas antes de decidir.

| paso | metrica | valor | fuente |
|---|---|---|---|
| 10. Particion aleatoria | accuracy | 0.9999 | `baseline_v1.json` |
| 10. Particion por comercio | accuracy | 0.4675 | `baseline_v1.json` |
| 10. CV agrupada 5-fold | f1_macro | 0.3837 +/- 0.0987 | `cv_agrupada_comercio.json` |
| 10. Calibracion OOD | ECE / Brier | 0.3890 / 0.1083 | `calibracion.json` |
| 10. Umbral 0.8 | accuracy aceptadas | 0.4802 (cobertura 0.5882) vs. 0.3977 global | `calibracion.json` |

---

## Resumen de la linea de tiempo (modelo de ocho categorias)

| paso | metrica | valor | fuente |
|---|---|---|---|
| 1. Particion aleatoria | accuracy | 0.9999 | `baseline_v1.json` |
| 2. Diagnostico de fuga | -- | cada comercio = 1 categoria | `notebook.ipynb` seccion 10.2 |
| 3. Particion por comercio | accuracy | 0.4125 | `baseline_v1.json` |
| 3. CV agrupada 5-fold | accuracy | 0.4276 +/- 0.0733 | `cv_agrupada_comercio.json` |
| 4. Categoria mas fuerte / mas debil (OOD) | f1-score | servicios 0.5776 / otras 0.1606 | `metricas_por_categoria.md` |
| 5. Calibracion OOD | ECE / Brier | 0.3335 / 0.1152 | `calibracion.json` |
| 6. Mejor alternativa de algoritmo | f1_macro | 0.4007 (vigente) vs. 0.3934 (siguiente mejor) | `benchmark_clasico.md` |
| 6. Mejor alternativa con features | f1_macro | +0.0102 maximo (dentro de ruido) | `benchmark_con_features.md` |
| 7. Causa dominante de error | % de la muestra | 76.4% comercio desconocido | `analisis_errores.md` |
| 8. Decision | -- | no reentrenar, falta diversidad real de comercios | `decision_reentrenamiento.md` |
| 9. Mitigacion operativa | -- | `estado_confianza` (aceptado/requiere_revision/otras) | Fase 12, `srv-python` y `srv-java` |
