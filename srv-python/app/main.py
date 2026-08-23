"""ml-service: inferencia para el orquestador Java (finance-ai-api).

Campos en snake_case, iguales a los del reto y al enum FinancialCategory del
backend.

  POST /clasificar  recibe solo transacciones -> no ve ingreso ni deuda.
  POST /perfil      recibe solo agregados     -> no ve descripciones crudas.

Ninguno de los dos ve al usuario completo; solo el backend Java lo hace.
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Literal, NamedTuple, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

_AQUI = Path(__file__).resolve().parent
for _c in (_AQUI / "ciencia_datos", _AQUI.parent.parent / "ciencia-datos"):
    if (_c / "features.py").exists():
        sys.path.insert(0, str(_c))
        break

import features  # noqa: E402

from .modelos import registro  # noqa: E402
from .reglas import clasificar_por_reglas  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("financeai.ml")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # En el arranque, no por peticion: joblib.load del pipeline TF-IDF cuesta
    # cientos de milisegundos.
    registro.cargar()
    log.info("ml-service listo (origen=%s, version=%s)", registro.origen, registro.version)
    yield


app = FastAPI(
    title="FinanceAI ml-service",
    version="1.0.0",
    description=(
        "Clasificacion de gastos y evaluacion de perfil financiero. "
        "Los modelos se publican en OCI Object Storage y se descargan al arrancar."
    ),
    lifespan=ciclo_de_vida,
)

# Se construye desde features.CATEGORIAS para que la documentacion OpenAPI y
# el modelo entrenado no discrepen.
Categoria = Enum("Categoria", {c: c for c in features.CATEGORIAS}, type=str)

#: Estado explicito de confianza (Fase 12, estrategia de abstencion). Ver
#: `_estado_confianza` para los cortes y su justificacion con calibracion.json.
EstadoConfianza = Literal["aceptado", "requiere_revision", "otras"]


# ---------------------------------------------------------------- esquemas
class Transaccion(BaseModel):
    descripcion: str = Field(min_length=1, max_length=200, examples=["Supermercado Exito"])
    valor: float = Field(gt=0, examples=[420])


class ClasificarRequest(BaseModel):
    """Particion 'necesidad de saber': SOLO transacciones."""
    transacciones: list[Transaccion] = Field(min_length=1, max_length=5000)


class CategoriaTop(BaseModel):
    """Una entrada del top3 (Fase 16): candidata y su confianza [0,1]."""
    categoria: Categoria
    confianza: float = Field(ge=0, le=1, examples=[0.97])


class TransaccionClasificada(Transaccion):
    categoria: Categoria
    confianza: float = Field(ge=0, le=1, examples=[0.97])
    origen: str = Field(examples=["modelo"], description="modelo | reglas")
    estado_confianza: EstadoConfianza = Field(
        examples=["aceptado"],
        description=(
            "aceptado (confianza >= umbral_confianza_alta, 0.8 por defecto) | "
            "requiere_revision (umbral_confianza <= confianza < umbral_confianza_alta) | "
            "otras (confianza < umbral_confianza, 0.5 por defecto; mismo corte que ya "
            "degrada la categoria a 'otras', sin cambios de comportamiento)"
        ),
    )
    top3: list[CategoriaTop] = Field(
        min_length=1, max_length=3,
        examples=[[{"categoria": "alimentacion", "confianza": 0.97}]],
        description=(
            "Hasta 3 categorias mas probables segun predict_proba del "
            "clasificador calibrado, ordenadas de forma descendente por "
            "confianza. La primera entrada coincide siempre con `categoria` "
            "(la decision final, ya aplicados el umbral y las reglas de "
            "respaldo). En modo reglas o degradado (sin clasificador "
            "cargado, o el propio respaldo por palabras clave) trae un solo "
            "elemento, con la categoria de la keyword y su confianza fija."
        ),
    )


class ClasificarResponse(BaseModel):
    transacciones_clasificadas: list[TransaccionClasificada]
    resumen_gastos: dict[str, float] = Field(
        description="Monto agregado por categoria, con las 8 categorias siempre presentes.",
        examples=[{"alimentacion": 420.0, "transporte": 300.0}],
    )


class PerfilRequest(BaseModel):
    """Particion 'necesidad de saber': SOLO agregados."""
    ingreso_mensual: float = Field(gt=0, examples=[4500])
    nivel_endeudamiento: float = Field(ge=0, le=100, examples=[25])
    frecuencia_ahorro: str = Field(examples=["Media"])
    resumen_gastos: dict[str, float] = Field(
        examples=[{"alimentacion": 420, "transporte": 300, "ocio": 40}]
    )

    @field_validator("frecuencia_ahorro")
    @classmethod
    def _frecuencia_valida(cls, v: str) -> str:
        try:
            return features.normalizar_frecuencia(v)
        except ValueError as e:
            raise ValueError(str(e)) from e


class Factor(BaseModel):
    nombre: str = Field(examples=["tasa_gasto"])
    valor: float = Field(examples=[0.76])
    impacto: str = Field(pattern="^(sube_riesgo|baja_riesgo)$", examples=["sube_riesgo"])


class PerfilResponse(BaseModel):
    perfil_financiero: str = Field(examples=["En observación"])
    probabilidad: float = Field(ge=0, le=1, examples=[0.82])
    factores: list[Factor]
    origen: str = Field(examples=["modelo"], description="modelo | reglas")


# --------------------------------------------------------------- endpoints
@app.get("/health", tags=["diagnostico"])
def health():
    """Liveness. No toca los modelos: debe responder aunque esten sin cargar."""
    return {"status": "ok", "modelo": registro.version, "origen": registro.origen}


@app.get("/modelo/info", tags=["diagnostico"])
def modelo_info():
    """Procedencia del modelo, metricas de entrenamiento y estado de OCI."""
    info = registro.info()
    info["referencia_saludable"] = registro.referencia_saludable
    return info


@app.get("/modelo/metricas", tags=["diagnostico"])
def modelo_metricas():
    """Resumen condensado de las metricas de evaluacion del modelo (Fase 16).

    Incluye baseline (particion aleatoria vs. comercio no visto), CV agrupada
    por comercio, matriz de confusion OOD, metricas por categoria, calibracion
    y benchmark contra modelos clasicos. Se genera sin conexion con
    `ciencia-datos/scripts/generar_resumen_metricas.py` a partir de los
    artefactos ya calculados en `ciencia-datos/experimentos/`; no reproduce
    las 58,894 filas de las predicciones out-of-fold, solo sus agregados.
    """
    resumen = registro.metricas_resumen()
    if resumen is None:
        raise HTTPException(status_code=404, detail="metricas_resumen.json no disponible")
    return resumen


@app.post("/clasificar", response_model=ClasificarResponse, tags=["inferencia"])
def clasificar(peticion: ClasificarRequest) -> ClasificarResponse:
    """Categoriza un lote de transacciones y devuelve el agregado por categoria."""
    descripciones = [t.descripcion for t in peticion.transacciones]
    resultados = _clasificar_lote(descripciones)

    clasificadas: list[TransaccionClasificada] = []
    # Solo se incluyen las categorias con gasto, igual que en el ejemplo del
    # reto y que en la respuesta del backend Java.
    resumen: dict[str, float] = {}
    umbral_revision = registro.umbral_confianza
    umbral_aceptado = registro.umbral_confianza_alta

    for transaccion, resultado in zip(peticion.transacciones, resultados):
        clasificadas.append(TransaccionClasificada(
            descripcion=transaccion.descripcion,
            valor=transaccion.valor,
            categoria=resultado.categoria,
            confianza=round(resultado.confianza, 4),
            origen=resultado.origen,
            estado_confianza=_estado_confianza(
                resultado.confianza, umbral_revision, umbral_aceptado
            ),
            top3=[
                CategoriaTop(categoria=categoria, confianza=round(confianza, 4))
                for categoria, confianza in resultado.top3
            ],
        ))
        resumen[resultado.categoria] = resumen.get(resultado.categoria, 0.0) + transaccion.valor

    return ClasificarResponse(
        transacciones_clasificadas=clasificadas,
        resumen_gastos={k: round(v, 2) for k, v in resumen.items()},
    )


@app.post("/perfil", response_model=PerfilResponse, tags=["inferencia"])
def perfil(peticion: PerfilRequest) -> PerfilResponse:
    """Evalua la salud financiera a partir de los agregados."""
    resumen = {c: float(peticion.resumen_gastos.get(c, 0.0) or 0.0) for c in features.CATEGORIAS}
    vector = features.construir_features_perfil(
        peticion.ingreso_mensual, peticion.nivel_endeudamiento,
        peticion.frecuencia_ahorro, resumen,
    )

    if registro.perfil is not None:
        resultado = _perfil_con_modelo(vector)
        if resultado is not None:
            return resultado

    return _perfil_con_reglas(vector)


# ----------------------------------------------------------------- interno
def _estado_confianza(confianza: float, umbral_revision: float, umbral_aceptado: float) -> str:
    """Estado explicito de confianza (Fase 12, estrategia de abstencion).

    Cortes tomados de ciencia-datos/experimentos/calibracion.json (Fase 5,
    tabla coverage_vs_accuracy sobre 58894 filas OOD, accuracy_global_ood =
    0.4264271402859374):

      - "aceptado": confianza >= umbral_aceptado (0.8 por defecto).
        accuracy_aceptadas en umbral=0.8 es 0.5223254795206358
        (31959 filas, coverage=0.5426529018236154): +9.59 puntos absolutos
        sobre el global (+22.5% relativo). En umbral=0.9 la accuracy sube a
        0.5669816157621036 pero el coverage cae a 0.4636465514313852; 0.8 es
        el mejor punto que sigue aceptando mas de la mitad del trafico.
      - "requiere_revision": umbral_revision <= confianza < umbral_aceptado.
        En el propio umbral_revision (0.5, el mismo que ya usa el fallback a
        'otras') la accuracy_aceptadas es 0.45240417540000416
        (48187 filas, coverage=0.8181987978401875): mejor que el azar entre 8
        categorias pero no lo bastante fiable para aceptar sin marcar.
      - "otras": confianza < umbral_revision. Sin cambios de comportamiento:
        la categoria ya se degradaba a 'otras' en este rango.
    """
    if confianza >= umbral_aceptado:
        return "aceptado"
    if confianza >= umbral_revision:
        return "requiere_revision"
    return "otras"


class ResultadoClasificacion(NamedTuple):
    """Salida interna de `_clasificar_lote`, una por transaccion."""
    categoria: str
    confianza: float
    origen: str
    top3: list[tuple[str, float]]


def _top3_desde_fila(
    fila,
    clases: list[str],
    categoria_principal: str,
    confianza_principal: float,
    limite: int = 3,
) -> list[tuple[str, float]]:
    """Hasta `limite` (categoria, probabilidad) desde una fila de predict_proba.

    Ordenadas de forma descendente por probabilidad, con `categoria_principal`
    siempre de primera y con `confianza_principal` (que puede no coincidir con
    la probabilidad cruda de esa categoria en `fila`: por ejemplo cuando el
    umbral degrada la categoria a "otras" sin cambiar la confianza reportada,
    ver `_clasificar_lote`). Asi el primer elemento del top3 coincide siempre
    con la decision final que ya viaja en `categoria`/`confianza`.
    """
    pares = sorted(
        ((features.normalizar_categoria(c), float(p)) for c, p in zip(clases, fila)),
        key=lambda par: par[1],
        reverse=True,
    )
    top3 = [(categoria_principal, confianza_principal)]
    vistas = {categoria_principal}
    for categoria, prob in pares:
        if categoria in vistas:
            continue
        vistas.add(categoria)
        top3.append((categoria, prob))
        if len(top3) == limite:
            break
    return top3


def _clasificar_lote_por_reglas(descripciones: list[str]) -> list[ResultadoClasificacion]:
    """Camino sin modelo: todo por palabras clave. `top3` trae un solo elemento
    (Fase 16), la propia categoria de la regla, ya que no hay distribucion de
    probabilidades que ofrecer."""
    salida: list[ResultadoClasificacion] = []
    for d in descripciones:
        categoria, confianza = clasificar_por_reglas(d)
        salida.append(ResultadoClasificacion(categoria, confianza, "reglas", [(categoria, confianza)]))
    return salida


def _clasificar_lote(descripciones: list[str]) -> list[ResultadoClasificacion]:
    """Devuelve (categoria, confianza, origen, top3) por descripcion.

    Un solo predict_proba para todo el lote; una llamada por transaccion
    multiplicaria por N el coste de vectorizar.
    """
    if registro.clasificador is None:
        return _clasificar_lote_por_reglas(descripciones)

    normalizadas = [features.normalizar_texto(d) for d in descripciones]

    try:
        probabilidades = registro.clasificador.predict_proba(normalizadas)
        clases = list(registro.clasificador.classes_)
    except Exception:
        log.exception("Fallo la inferencia del clasificador; se responde con reglas.")
        return _clasificar_lote_por_reglas(descripciones)

    umbral = registro.umbral_confianza
    salida: list[ResultadoClasificacion] = []

    for original, normalizada, fila in zip(descripciones, normalizadas, probabilidades):
        indice = int(fila.argmax())
        categoria = features.normalizar_categoria(clases[indice])
        confianza = float(fila[indice])

        if not normalizada:
            # Descripcion vacia tras normalizar: no hay nada que clasificar.
            salida.append(ResultadoClasificacion("otras", 0.0, "reglas", [("otras", 0.0)]))
            continue

        if confianza < umbral:
            # El modelo duda. Antes de caer en "otras" se prueba con la regla.
            categoria_regla, confianza_regla = clasificar_por_reglas(original)
            if categoria_regla != "otras":
                salida.append(ResultadoClasificacion(
                    categoria_regla, confianza_regla, "reglas",
                    [(categoria_regla, confianza_regla)],
                ))
            else:
                top3 = _top3_desde_fila(fila, clases, "otras", confianza)
                salida.append(ResultadoClasificacion("otras", confianza, "modelo", top3))
            continue

        top3 = _top3_desde_fila(fila, clases, categoria, confianza)
        salida.append(ResultadoClasificacion(categoria, confianza, "modelo", top3))

    return salida


def _perfil_con_modelo(vector: dict[str, float]) -> Optional[PerfilResponse]:
    """Predice con el modelo serializado. Devuelve None si algo falla."""
    try:
        import numpy as np

        x = np.array([[vector[c] for c in features.COLUMNAS_PERFIL]], dtype=float)
        modelo = registro.perfil

        probabilidades = modelo.predict_proba(x)[0]
        clases = list(modelo.classes_)
        indice = int(probabilidades.argmax())
        etiqueta = features.normalizar_perfil(clases[indice])

        return PerfilResponse(
            perfil_financiero=etiqueta,
            probabilidad=round(float(probabilidades[indice]), 4),
            factores=_factores_del_modelo(x, modelo, clases, vector),
            origen="modelo",
        )
    except Exception:
        log.exception("Fallo la inferencia del perfil; se responde con umbrales.")
        return None


def _factores_del_modelo(x, modelo, clases, vector) -> list[Factor]:
    """Contribucion de cada atributo a la clase 'En riesgo'.

    En una logistica sobre datos estandarizados, coeficiente x valor
    estandarizado es la contribucion al logit. Se toman los tres mayores en
    valor absoluto y se reporta el valor crudo del atributo.

    Sobre `impacto`: al estandarizar, el valor queda centrado en la media de la
    poblacion de entrenamiento, asi que un endeudamiento del 35% puede salir
    como "baja_riesgo" si la media esta por encima. Se lee "comparado con el
    usuario promedio". Ver docs/API-ENDPOINTS.md.

    Si el pipeline no tiene la forma esperada, cae a los factores heuristicos.
    """
    try:
        escalador = modelo.named_steps["escalador"]
        clf = modelo.named_steps["clf"]
        indice_riesgo = clases.index("En riesgo")

        estandarizado = escalador.transform(x)[0]
        contribuciones = clf.coef_[indice_riesgo] * estandarizado

        orden = sorted(
            range(len(features.COLUMNAS_PERFIL)),
            key=lambda i: abs(contribuciones[i]),
            reverse=True,
        )[:3]

        return [
            Factor(
                nombre=features.COLUMNAS_PERFIL[i],
                valor=round(float(vector[features.COLUMNAS_PERFIL[i]]), 4),
                impacto="sube_riesgo" if contribuciones[i] > 0 else "baja_riesgo",
            )
            for i in orden
        ]
    except Exception:
        log.warning("No se pudieron derivar factores del modelo; se usan los heuristicos.")
        return _factores_heuristicos(vector)


def _perfil_con_reglas(vector: dict[str, float]) -> PerfilResponse:
    """Umbrales de respaldo, identicos a los de ProfileService.java para que
    backend y ml-service no den diagnosticos distintos."""
    deuda = vector["ratio_endeudamiento"] * 100
    tasa = vector["tasa_gasto"]

    if deuda >= 50 or tasa >= 1.0:
        etiqueta, probabilidad = "En riesgo", 0.75
    elif deuda >= 30 or tasa >= 0.8:
        etiqueta, probabilidad = "En observación", 0.82
    else:
        etiqueta, probabilidad = "Saludable", 0.90

    return PerfilResponse(
        perfil_financiero=etiqueta,
        probabilidad=probabilidad,
        factores=_factores_heuristicos(vector),
        origen="reglas",
    )


def _factores_heuristicos(vector: dict[str, float]) -> list[Factor]:
    ahorro_suficiente = vector["ahorro_ordinal"] >= 2
    return [
        Factor(nombre="relacion_deuda_ingreso", valor=round(vector["ratio_endeudamiento"], 3),
               impacto="sube_riesgo" if vector["ratio_endeudamiento"] >= 0.30 else "baja_riesgo"),
        Factor(nombre="tasa_gasto", valor=round(vector["tasa_gasto"], 3),
               impacto="sube_riesgo" if vector["tasa_gasto"] >= 0.80 else "baja_riesgo"),
        Factor(nombre="frecuencia_ahorro", valor=1.0 if ahorro_suficiente else 0.0,
               impacto="baja_riesgo" if ahorro_suficiente else "sube_riesgo"),
    ]
