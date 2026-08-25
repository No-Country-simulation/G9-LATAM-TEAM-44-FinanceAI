# Arquitectura

Notas sobre por qué el sistema está montado así. El *qué* está en los README de cada
servicio.

```
┌───────────┐   HTTP    ┌──────────────┐   HTTP    ┌────────────────┐
│  web      │ ────────► │  srv-java    │ ────────► │  srv-python    │
│  :8081    │           │  :8080       │           │  :8000         │
│           │ ◄──────── │              │ ◄──────── │                │
│ nginx +   │           │ Spring Boot  │           │ FastAPI        │
│ estático  │           │ orquestador  │           │ inferencia     │
└───────────┘           └──────┬───────┘           └───────┬────────┘
                               │                           │
                               │  archiva análisis         │  descarga modelos
                               ▼                           ▼
                        ┌──────────────────────────────────────┐
                        │       OCI Object Storage             │
                        │  finance-ai-models/                  │
                        │    clasificador_gastos.joblib        │
                        │    modelo_perfil.joblib              │
                        │    metadatos.json                    │
                        │    historial/AAAA/MM/DD/*.json       │
                        └──────────────────────────────────────┘
```

---

## Por qué dos servicios

Se podía haber servido el modelo desde Java (ONNX, DJL) o escrito toda la API en Python.
Elegimos separar por tres motivos:

1. El modelo se entrena en Python y el pipeline serializado incluye el vectorizador TF-IDF de
   scikit-learn. Reimplementarlo en Java para servirlo abre la puerta a que la transformación
   en producción no sea la del entrenamiento.
2. Los ciclos de vida son distintos. Publicar un modelo reentrenado es subir un objeto al
   bucket y reiniciar un contenedor; no toca el backend.
3. El reto pide Java con Spring Boot para la API y Python para la ciencia de datos.

El coste es una llamada de red más por análisis y un servicio más que se puede caer. Lo
segundo se cubre con el modo degradado; lo primero, llamando por lote (dos peticiones por
análisis, no dos por transacción).

---

## Partición de la información

| Paso | Quién | Qué ve | Qué no ve |
|---|---|---|---|
| 1 | `POST /clasificar` | descripciones y montos | ingreso, deuda, identidad |
| 2 | agregación | ambos | — (ocurre en Java) |
| 3 | `POST /perfil` | agregados por categoría | descripciones crudas |
| 4 | recomendaciones | todo | — (ocurre en Java) |

Ningún componente de inferencia ve al usuario completo. La descripción de una transacción
dice dónde estuvo alguien y qué compró; el ingreso y la deuda dicen su situación. Por
separado son datos sueltos.

Solo el backend Java tiene la foto completa, así que es el único sitio donde hay que auditar
el tratamiento de datos personales.

En la misma línea, el historial archivado en Object Storage guarda perfil, agregados e
indicadores, pero no las descripciones. Para seguir la evolución financiera no hacen falta.

---

## Una sola fuente para las features

`ciencia-datos/features.py` lo importan el notebook y el ml-service. No se duplica.

Si el notebook normalizara el texto de una forma y la API de otra, el modelo recibiría en
producción vectores distintos a los del entrenamiento. Eso no lanza error, no aparece en los
tests y no lo detecta ninguna métrica offline: el modelo simplemente acierta menos.

Alrededor de esa decisión hay tres apoyos:

- El `Dockerfile` de `srv-python` construye desde la raíz del repositorio para poder copiar
  ese archivo dentro de la imagen.
- `metadatos.json` guarda el orden exacto de `COLUMNAS_PERFIL` y el servicio lo valida al
  cargar. Si no coincide, no usa el artefacto.
- `srv-python/tests/test_features.py` fija el comportamiento de la normalización.

---

## El vector de atributos no lleva montos

Las 17 columnas de `COLUMNAS_PERFIL` son ratios, porcentajes y conteos. Ninguna es una
cantidad de dinero.

El formulario deja elegir moneda pero no convierte, así que el mismo sueldo llega como
`3.000` o como `12.000.000` según se escriba en dólares o en pesos colombianos. Mientras el
vector llevó `ingreso_mensual`, `gasto_total` y `carga_deuda_absoluta` en crudo, esas cifras
caían fuera del rango de entrenamiento (ingresos de 1.200 a 7.000), el `StandardScaler` las
convertía en z-scores enormes y la regresión logística saturaba. El resultado era que la
misma situación económica recibía un diagnóstico distinto según la unidad en que estuviera
escrita, con una confianza cercana al 100% justo donde el modelo menos debía confiar.

Sobre ratios eso no puede reproducirse: el factor de conversión aparece arriba y abajo de la
división y se cancela. `srv-python/tests/test_features.py` lo fija con un test que compara el
vector a cinco escalas distintas.

La contrapartida es que el modelo no puede usar el nivel de ingreso como señal. En este
proyecto no cuesta nada, porque la regla que genera la etiqueta en el dataset sintético
tampoco lo usa. Con datos reales sí sería una señal legítima, y entonces la salida no es
devolver los montos al vector sino convertir a una moneda de referencia antes de construirlo.

---

## Degradación en capas

| Nivel | Cuándo | Qué usa | Señal |
|---|---|---|---|
| Completo | todo bien | modelos entrenados | `modo_degradado: false` |
| Degradado | ml-service caído | reglas por palabras clave + umbrales, en Java | `modo_degradado: true` |
| Reducido | ml-service vivo, sin artefactos | reglas, en Python | `origen: "reglas"` en `/modelo/info` |

La forma de la respuesta no cambia entre niveles, así que el frontend solo lee
`modo_degradado` y muestra un aviso.

Los umbrales de respaldo de Java y los de Python son idénticos. Si el respaldo diera un
diagnóstico distinto según quién lo calcule, sería peor que no tener respaldo.

---

## El umbral de confianza

El notebook (sección 10.2) mide que el clasificador cae de 0.9999 de accuracy a 0.41 ante
comercios que nunca vio. De ahí salen dos cosas:

- Degradar a `otras` por debajo de 0.5. Un gasto sin clasificar se ve y se corrige; uno mal
  atribuido contamina el análisis sin que nadie lo note.
- Consultar las palabras clave antes de caer en `otras`, porque cubren con certeza los
  comercios frecuentes.

Sin la evaluación por comercio nos habríamos quedado con el 99,9% y ninguna de las dos
protecciones existiría.

---

## Dónde vive cada tipo de lógica

| Tipo | Dónde | Por qué |
|---|---|---|
| Transformación de features | `ciencia-datos/features.py` | Compartida entre entrenamiento e inferencia |
| Predicción | `srv-python` | Donde vive el artefacto serializado |
| Validación de entrada | `srv-java` (Bean Validation) | Rechazar temprano, con un 400 útil, antes de gastar una llamada de red |
| Reglas de negocio | `srv-java` (`RecommendationService`) | Auditables y modificables sin reentrenar |
| Umbrales de comparación | notebook → constantes en Java | Salen de los datos, se aplican como regla |
| Presentación | `web` | — |

Las recomendaciones no las genera el modelo. Una recomendación financiera hay que poder
explicarla ante un usuario y revisarla ante un regulador. Lo que sí viene de los datos son
los umbrales: `PATRON_SALUDABLE` es la mediana del peso de cada categoría entre los usuarios
sanos, calculada en el notebook.

---

## El modelo como dato

La imagen de `srv-python` no contiene los modelos, los descarga de Object Storage al arrancar.

Publicar un modelo reentrenado es subir un objeto y reiniciar un contenedor: no hay que
reconstruir imágenes ni redesplegar el backend.

El orden de resolución (OCI → local → reglas) evita que esto sea frágil: en desarrollo se
trabaja con los artefactos del notebook sin tocar la nube.

---

## Decisiones y contrapartidas

| Decisión | Se gana | Se paga |
|---|---|---|
| Dos servicios | Sin reimplementar el pipeline; despliegue independiente | Una llamada de red más; un servicio más que vigilar |
| PAR en vez del SDK de OCI en Java | Sin credenciales en el contenedor ni decenas de MB de SDK | La PAR caduca; no se pueden listar objetos |
| Frontend sin build | Nada que compilar el día de la demo | Sin componentes, sin tipos, sin árbol de dependencias |
| Historial en Object Storage, no en BD | Cero infraestructura adicional | No hay consultas por usuario en tiempo real |
| Dataset sintético | Etiquetas de calidad y reproducibles | Las métricas no predicen el rendimiento real |
| Artefactos versionados en git (~3 MB) | Funciona al clonar, sin credenciales | Peso en el repositorio |
| Vector de atributos sin montos | El diagnóstico no depende de la moneda en que se escriba | El modelo no puede usar el nivel de ingreso como señal |

---

## Qué haría falta para producción

- Datos reales anonimizados. Todo lo demás va después de esto.
- Autenticación y multiusuario. Hoy cada petición es independiente y anónima.
- Base de datos para el historial por usuario, con Object Storage como archivo frío.
- Monitorización de deriva: comparar la distribución de confianzas en producción contra la
  del entrenamiento. Una caída sostenida indica comercios nuevos y necesidad de reentrenar.
- Atributos temporales. Hoy cada periodo se evalúa por separado, y detectar que un usuario
  empeora mes a mes vale más que clasificar bien un mes aislado.
