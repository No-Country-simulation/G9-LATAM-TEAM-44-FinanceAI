"""FinanceAI · ml-service (contrato) — v0.1

Define y hace ejecutable el contrato entre el orquestador Java (finance-ai-api)
y el servicio de AI. Los nombres de campos son snake_case (como el reto y el
documento de entidades). Las categorías replican el enum FinancialCategory del
backend: alimentacion, transporte, salud, vivienda, educacion, ocio, servicios,
otras. Los umbrales del perfil replican FinancialAnalysisService para que el
reemplazo del stub Java sea de comportamiento compatible desde el día 0.

Los TODO(DS)/TODO(ML) marcan dónde entran los artefactos reales.
"""
from enum import Enum
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator

app = FastAPI(
    title="FinanceAI ml-service (contrato)",
    version="0.1.0",
    description="Contrato ejecutable entre finance-ai-api (Java) y el servicio de AI.",
)

# ---------------------------------------------------------------- categorías
class Categoria(str, Enum):
    alimentacion = "alimentacion"
    transporte = "transporte"
    salud = "salud"
    vivienda = "vivienda"
    educacion = "educacion"
    ocio = "ocio"
    servicios = "servicios"
    otras = "otras"


KEYWORDS: dict[Categoria, list[str]] = {
    Categoria.alimentacion: ["supermercado", "comida", "restaurante", "mercado", "exito", "carulla", "d1", "panaderia", "rappi", "domicilio"],
    Categoria.transporte: ["combustible", "gasolina", "uber", "taxi", "terpel", "peaje", "transmilenio", "metro", "parqueadero", "bus"],
    Categoria.salud: ["farmacia", "hospital", "salud", "drogueria", "eps", "medico", "clinica", "odontologia"],
    Categoria.vivienda: ["arriendo", "alquiler", "hipoteca", "administracion", "renta"],
    Categoria.educacion: ["colegio", "universidad", "curso", "matricula", "udemy", "platzi", "libros"],
    Categoria.ocio: ["netflix", "cine", "streaming", "spotify", "disney", "hbo", "steam", "bar", "concierto", "juego"],
    Categoria.servicios: ["luz", "agua", "internet", "gas", "celular", "energia", "claro", "movistar", "tigo"],
}

PERFILES = ("Saludable", "En observación", "En riesgo")

MODELOS = {
    "clasificador": None,   # TODO(ML): joblib.load del pipeline TF-IDF + clasificador
    "perfil": None,         # TODO(ML): modelo tabular calibrado (o sesión ONNX)
    "version": "contrato-stub-0.1",
    "origen_esperado": "oci://finance-ai-models/financial-model.pkl",  # ver OCIStorageService (Java)
}


# ---------------------------------------------------------------- esquemas
class Transaccion(BaseModel):
    descripcion: str = Field(min_length=1, max_length=200, examples=["Supermercado"])
    valor: float = Field(gt=0, examples=[420])


class ClasificarRequest(BaseModel):
    """Partición 'necesidad de saber': SOLO transacciones. Sin ingreso, deuda ni identidad."""
    transacciones: list[Transaccion] = Field(min_length=1, max_length=5000)


class TransaccionClasificada(Transaccion):
    categoria: Categoria
    confianza: float = Field(ge=0, le=1, examples=[0.9])


class ClasificarResponse(BaseModel):
    transacciones_clasificadas: list[TransaccionClasificada]


class PerfilRequest(BaseModel):
    """Partición 'necesidad de saber': SOLO agregados. Sin descripciones crudas."""
    ingreso_mensual: float = Field(gt=0, examples=[4500])
    nivel_endeudamiento: float = Field(ge=0, le=100, examples=[25])
    frecuencia_ahorro: str = Field(examples=["Media"])
    resumen_gastos: dict[Categoria, float] = Field(
        examples=[{"alimentacion": 420, "transporte": 300, "ocio": 40}]
    )

    @field_validator("frecuencia_ahorro")
    @classmethod
    def _frecuencia_valida(cls, v: str) -> str:
        permitidas = {"alta", "media", "baja", "nula"}
        if v.strip().lower() not in permitidas:
            raise ValueError("frecuencia_ahorro debe ser Alta, Media, Baja o Nula")
        return v.strip().capitalize()


class Factor(BaseModel):
    nombre: str = Field(examples=["relacion_deuda_ingreso"])
    valor: float = Field(examples=[0.25])
    impacto: str = Field(pattern="^(sube_riesgo|baja_riesgo)$", examples=["sube_riesgo"])


class PerfilResponse(BaseModel):
    perfil_financiero: str = Field(examples=["En observación"])
    probabilidad: float = Field(ge=0, le=1, examples=[0.82])
    factores: list[Factor]


# ---------------------------------------------------------------- endpoints
@app.get("/health")
def health():
    return {"status": "ok", "modelo": MODELOS["version"]}


@app.get("/modelo/info")
def modelo_info():
    return {
        "version": MODELOS["version"],
        "clasificador_cargado": MODELOS["clasificador"] is not None,
        "perfil_cargado": MODELOS["perfil"] is not None,
        "origen_esperado": MODELOS["origen_esperado"],
        "categorias": [c.value for c in Categoria],
        "perfiles": list(PERFILES),
    }


@app.post("/clasificar", response_model=ClasificarResponse)
def clasificar(req: ClasificarRequest) -> ClasificarResponse:
    salida: list[TransaccionClasificada] = []
    for t in req.transacciones:
        if MODELOS["clasificador"] is not None:
            # TODO(ML): probas = pipeline.predict_proba([t.descripcion])
            # categoria, confianza = argmax + umbral (< 0.5 -> otras)
            categoria, confianza = _clasificar_stub(t.descripcion)
        else:
            categoria, confianza = _clasificar_stub(t.descripcion)
        salida.append(TransaccionClasificada(
            descripcion=t.descripcion, valor=t.valor,
            categoria=categoria, confianza=confianza,
        ))
    return ClasificarResponse(transacciones_clasificadas=salida)


@app.post("/perfil", response_model=PerfilResponse)
def perfil(req: PerfilRequest) -> PerfilResponse:
    total = float(sum(req.resumen_gastos.values()))
    ratio = total / req.ingreso_mensual if req.ingreso_mensual else 1.0

    if MODELOS["perfil"] is not None:
        # TODO(ML): x = vector de features (paridad con el notebook via features.py)
        # probas calibradas -> etiqueta + probabilidad; factores = SHAP/coeficientes top-3
        pass

    # Stub: mismos umbrales que FinancialAnalysisService (Java) para paridad de comportamiento.
    if req.nivel_endeudamiento >= 50 or ratio >= 1.0:
        etiqueta, proba = "En riesgo", 0.75
    elif req.nivel_endeudamiento >= 30 or ratio >= 0.8:
        etiqueta, proba = "En observación", 0.82
    else:
        etiqueta, proba = "Saludable", 0.90

    factores = [
        Factor(nombre="relacion_deuda_ingreso", valor=round(req.nivel_endeudamiento / 100, 3),
               impacto="sube_riesgo" if req.nivel_endeudamiento >= 30 else "baja_riesgo"),
        Factor(nombre="tasa_gasto", valor=round(ratio, 3),
               impacto="sube_riesgo" if ratio >= 0.8 else "baja_riesgo"),
        Factor(nombre="frecuencia_ahorro",
               valor=1.0 if req.frecuencia_ahorro in ("Alta", "Media") else 0.0,
               impacto="baja_riesgo" if req.frecuencia_ahorro in ("Alta", "Media") else "sube_riesgo"),
    ]
    return PerfilResponse(perfil_financiero=etiqueta, probabilidad=proba, factores=factores)


# ---------------------------------------------------------------- stub interno
def _clasificar_stub(descripcion: str) -> tuple[Categoria, float]:
    texto = descripcion.lower()
    for categoria, palabras in KEYWORDS.items():
        if any(p in texto for p in palabras):
            return categoria, 0.90
    return Categoria.otras, 0.40
