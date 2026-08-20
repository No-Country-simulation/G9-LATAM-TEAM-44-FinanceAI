"""Ingenieria de atributos compartida entre el notebook y srv-python.

La transformacion vive aqui y solo aqui, para que el vector que ve el modelo
en inferencia sea el mismo que vio al entrenar.

Solo usa la biblioteca estandar.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Mapping

# --------------------------------------------------------------- vocabulario

#: El orden fija las columnas pct_* del vector de perfil.
CATEGORIAS: tuple[str, ...] = (
    "alimentacion",
    "transporte",
    "salud",
    "vivienda",
    "educacion",
    "ocio",
    "servicios",
    "otras",
)

#: Con tilde, como los devuelve la API.
PERFILES: tuple[str, ...] = ("Saludable", "En observación", "En riesgo")

#: Gastos dificiles de recortar a corto plazo.
CATEGORIAS_ESENCIALES: tuple[str, ...] = ("vivienda", "alimentacion", "salud", "servicios")

#: Gastos sobre los que una recomendacion puede actuar este mes.
CATEGORIAS_DISCRECIONALES: tuple[str, ...] = ("ocio", "otras")

#: Escala ordinal, no one-hot: hay orden real entre los niveles.
ESCALA_AHORRO: dict[str, int] = {"nula": 0, "baja": 1, "media": 2, "alta": 3}


# ------------------------------------------------------- normalizacion texto

# Prefijos tipicos de un extracto bancario.
_PREFIJOS_RUIDO = re.compile(
    r"\b(trf|pos|compra|pago|debito|credito|tarj|ref|aut|nro|no|cod)\b[\s:/#.-]*",
    flags=re.IGNORECASE,
)
_BASURA = re.compile(r"[^a-z0-9\s]+")
# Sin \b porque las referencias vienen pegadas a letras ("REF483920"). Desde 4
# digitos para no tocar "Microsoft 365" ni "D1".
_NUMEROS_LARGOS = re.compile(r"\d{4,}")
_ESPACIOS = re.compile(r"\s+")


def quitar_tildes(texto: str) -> str:
    """Elimina los diacriticos: 'Farmacía' y 'Farmacia' son el mismo token."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def normalizar_texto(texto: object) -> str:
    """Normaliza la descripcion de una transaccion para el vectorizador.

    Minusculas, sin tildes, sin prefijos de extracto ni puntuacion, y las
    referencias numericas largas colapsadas a un token '<num>' para que no
    inflen el vocabulario.

    Devuelve cadena vacia si no hay nada aprovechable; quien llama decide (en
    la practica, categoria 'otras').
    """
    if texto is None:
        return ""
    # Se mira la representacion en texto: pandas.NA lanza TypeError al
    # evaluarse como booleano, asi que `texto != texto` no sirve.
    s = str(texto)
    # 'nan', '<NA>' y 'NaT' llegan hasta aqui y acabarian como el token 'na'.
    if s.strip().lower() in ("", "nan", "<na>", "nat", "none", "null", "desconocido"):
        return ""

    # El orden no es intercambiable: la puntuacion se limpia antes de insertar
    # <num> (o se borrarian los angulos), y los digitos antes que los prefijos
    # (para que "REF" quede suelto y la regla lo pille).
    s = quitar_tildes(s).lower()
    s = _BASURA.sub(" ", s)
    s = _NUMEROS_LARGOS.sub(" <num> ", s)
    s = _PREFIJOS_RUIDO.sub(" ", s)
    s = _ESPACIOS.sub(" ", s).strip()
    return s


def normalizar_categoria(valor: object) -> str:
    """Lleva 'Alimentación' o 'ALIMENTACION' a la forma canonica."""
    s = quitar_tildes(str(valor or "")).strip().lower()
    return s if s in CATEGORIAS else "otras"


def normalizar_perfil(valor: object) -> str:
    """Devuelve la etiqueta canonica, acepte tilde o no.

    El generador de datos escribe 'En observacion' y la API 'En observación'.
    """
    s = quitar_tildes(str(valor or "")).strip().lower()
    if s.startswith("salud"):
        return "Saludable"
    if s.startswith("en observ") or s.startswith("observ"):
        return "En observación"
    if s.startswith("en riesg") or s.startswith("riesg"):
        return "En riesgo"
    raise ValueError(f"Perfil desconocido: {valor!r}")


def normalizar_frecuencia(valor: object) -> str:
    """Devuelve Alta / Media / Baja / Nula sea cual sea la capitalizacion."""
    s = quitar_tildes(str(valor or "")).strip().lower()
    if s not in ESCALA_AHORRO:
        raise ValueError(f"frecuencia_ahorro debe ser Alta, Media, Baja o Nula (llego {valor!r})")
    return s.capitalize()


# --------------------------------------------------- features del perfil

#: El modelo serializado depende de este orden. Reordenar obliga a reentrenar.
COLUMNAS_PERFIL: tuple[str, ...] = (
    "ingreso_mensual",
    "ratio_endeudamiento",
    "ahorro_ordinal",
    "gasto_total",
    "tasa_gasto",
    "capacidad_ahorro",
    "gasto_esencial_pct",
    "gasto_discrecional_pct",
    "concentracion_gasto",
    "categorias_activas",
    "vivienda_sobre_ingreso",
    "carga_deuda_absoluta",
) + tuple(f"pct_{c}" for c in CATEGORIAS)


def construir_features_perfil(
    ingreso_mensual: float,
    nivel_endeudamiento: float,
    frecuencia_ahorro: str,
    resumen_gastos: Mapping[str, float],
) -> dict[str, float]:
    """Construye el vector de atributos del modelo de perfil.

    Usa solo los cuatro datos que llegan en la peticion. Nada que no se pueda
    calcular en inferencia entra aqui.

    Args:
        ingreso_mensual: ingreso mensual neto, > 0.
        nivel_endeudamiento: porcentaje 0-100 comprometido en deuda.
        frecuencia_ahorro: Alta | Media | Baja | Nula.
        resumen_gastos: monto agregado por categoria canonica.

    Returns:
        Diccionario ordenado segun COLUMNAS_PERFIL.
    """
    ingreso = float(ingreso_mensual) if ingreso_mensual else 0.0
    if ingreso <= 0:
        # Evita la division por cero y deja las tasas en el extremo pesimista.
        ingreso = 1e-9

    gastos = {c: float(resumen_gastos.get(c, 0.0) or 0.0) for c in CATEGORIAS}
    total = sum(gastos.values())

    porcentajes = {c: (gastos[c] / total if total > 0 else 0.0) for c in CATEGORIAS}

    esencial = sum(porcentajes[c] for c in CATEGORIAS_ESENCIALES)
    discrecional = sum(porcentajes[c] for c in CATEGORIAS_DISCRECIONALES)

    # Herfindahl: 1 = todo en una categoria, 0.125 = repartido entre las ocho.
    concentracion = sum(p * p for p in porcentajes.values())
    activas = sum(1 for c in CATEGORIAS if gastos[c] > 0)

    ratio_deuda = float(nivel_endeudamiento) / 100.0
    tasa_gasto = total / ingreso

    features: dict[str, float] = {
        "ingreso_mensual": ingreso,
        "ratio_endeudamiento": ratio_deuda,
        "ahorro_ordinal": float(ESCALA_AHORRO[normalizar_frecuencia(frecuencia_ahorro).lower()]),
        "gasto_total": total,
        "tasa_gasto": tasa_gasto,
        # Negativa cuando gasta mas de lo que ingresa. No se recorta a 0.
        "capacidad_ahorro": 1.0 - tasa_gasto,
        "gasto_esencial_pct": esencial,
        "gasto_discrecional_pct": discrecional,
        "concentracion_gasto": concentracion,
        "categorias_activas": float(activas),
        "vivienda_sobre_ingreso": gastos["vivienda"] / ingreso,
        "carga_deuda_absoluta": ratio_deuda * ingreso,
    }
    for c in CATEGORIAS:
        features[f"pct_{c}"] = porcentajes[c]

    return {k: features[k] for k in COLUMNAS_PERFIL}


def vector_perfil(
    ingreso_mensual: float,
    nivel_endeudamiento: float,
    frecuencia_ahorro: str,
    resumen_gastos: Mapping[str, float],
) -> list[float]:
    """Como construir_features_perfil, pero ya en lista para `predict`."""
    f = construir_features_perfil(
        ingreso_mensual, nivel_endeudamiento, frecuencia_ahorro, resumen_gastos
    )
    return [f[c] for c in COLUMNAS_PERFIL]


def agregar_por_categoria(
    transacciones: Iterable[Mapping[str, object]],
    clave_categoria: str = "categoria",
    clave_monto: str = "monto",
) -> dict[str, float]:
    """Suma montos por categoria, siempre con las ocho claves presentes."""
    resumen = {c: 0.0 for c in CATEGORIAS}
    for t in transacciones:
        categoria = normalizar_categoria(t.get(clave_categoria))
        resumen[categoria] += abs(float(t.get(clave_monto, 0.0) or 0.0))
    return resumen
