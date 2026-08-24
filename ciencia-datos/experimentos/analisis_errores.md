# Analisis manual de errores (Fase 11)

Muestra de **72 errores** (de 33,780 errores totales sobre 58,894 filas entrenables evaluadas OOF, CV agrupada por comercio, Fase 2), estratificada por categoria real y por nivel de confianza (`prob_max`) para cubrir variedad en vez de tomar solo los primeros N por indice.

## Distribucion de causas probables

| causa_probable | n errores en la muestra | % de la muestra |
|---|---|---|
| comercio_desconocido_en_vocabulario | 55 | 76.4% |
| categoria_ambigua | 13 | 18.1% |
| texto_insuficiente | 2 | 2.8% |
| keyword_compartido_entre_categorias | 2 | 2.8% |
| posible_error_de_etiqueta | 0 | 0.0% |

## Distribucion por categoria real cubierta

| categoria_real | n errores en la muestra |
|---|---|
| alimentacion | 9 |
| educacion | 9 |
| ocio | 9 |
| otras | 9 |
| salud | 9 |
| servicios | 9 |
| transporte | 9 |
| vivienda | 9 |

## Que sugiere cada causa (accion recomendada)

### comercio_desconocido_en_vocabulario (55 casos en la muestra)

Mas datos: sumar comercios adicionales (o variantes de nombre) por categoria para que el vectorizador vea mas vocabulario compartido; en produccion, considerar un fallback basado en reglas/diccionario de comercios conocidos para las categorias con pocos comercios (educacion, servicios, vivienda).

### categoria_ambigua (13 casos en la muestra)

Revisar el criterio de etiquetado para esos comercios (podria requerir una categoria mixta o reglas de desambiguacion), o aceptar que el techo de accuracy para esas categorias es mas bajo y reportarlo como limite conocido del dataset.

### texto_insuficiente (2 casos en la muestra)

Enriquecer la descripcion antes de vectorizar (ej. concatenar el nombre del comercio completo, o pedir al banco/fuente mas contexto); si no hay mas texto disponible, backoff a un modelo que use el comercio como feature categorica directa en vez de solo el texto libre.

### keyword_compartido_entre_categorias (2 casos en la muestra)

Mejorar el vectorizador: ponderar mas el nombre del comercio que palabras genericas (ej. via un feature adicional de comercio, o eliminando/downweighting palabras de alta frecuencia cruzada tipo 'suscripcion', 'seguro', 'impuesto', 'taller', 'recarga').

### posible_error_de_etiqueta (0 casos en la muestra)

Auditar manualmente la etiqueta declarada para esas transacciones especificas antes de re-entrenar; si se confirma el error, corregir en el dataset fuente.

## Nota sobre `posible_error_de_etiqueta`

Se verifico, sobre las 58,894 filas entrenables completas, cuantas categorias distintas declara cada uno de los 159 comercios: **el 100% de los comercios (159/159) tiene una unica categoria en el 100% de sus transacciones** (no hay ningun comercio con `categoria` inconsistente entre filas). Por eso esta causa no se asigno a ningun error de la muestra: no hay evidencia de etiquetas inconsistentes en este dataset sintetico, los errores vienen de que el comercio es nuevo para el modelo (CV agrupada) y/o de vocabulario compartido entre categorias, no de datos mal etiquetados.

## Archivos generados

- `ciencia-datos/experimentos/analisis_errores.csv`: la muestra completa, una fila por error.
