"""Clasificador de respaldo por palabras clave.

Se usa sin modelo cargado y tambien cuando el modelo predice con poca
confianza: ante un comercio nuevo el modelo se desploma (ver la seccion 10.2
del notebook), y estas reglas cubren los frecuentes con certeza.

Espejo de FallbackClassifier.java. Las palabras nuevas hay que anadirlas en
ambos sitios.
"""
from __future__ import annotations

import sys
from pathlib import Path

_AQUI = Path(__file__).resolve().parent
for _c in (_AQUI / "ciencia_datos", _AQUI.parent.parent / "ciencia-datos"):
    if (_c / "features.py").exists():
        sys.path.insert(0, str(_c))
        break

from features import normalizar_texto  # noqa: E402

#: El orden importa: gana la primera categoria que haga match.
KEYWORDS: dict[str, list[str]] = {
    "alimentacion": [
        "supermercado", "comida", "restaurante", "mercado", "exito", "carulla",
        "d1", "panaderia", "rappi", "domicilio", "jumbo", "oxxo", "walmart",
        "soriana", "tottus", "mcdonalds", "burger", "pizza", "cafe", "fruteria",
        "carniceria", "minimarket", "ara",
    ],
    "transporte": [
        "combustible", "gasolina", "gasolinera", "uber", "taxi", "terpel",
        "peaje", "transmilenio", "metro", "parqueadero", "bus", "pemex",
        "primax", "shell", "petrobras", "ypf", "copec", "didi", "cabify",
        "indrive", "subte", "llantas", "mecanico", "soat", "bencina",
    ],
    "salud": [
        "farmacia", "hospital", "salud", "drogueria", "eps", "medico", "clinica",
        "odontologia", "inkafarma", "farmacity", "ahumada", "laboratorio",
        "optica", "dental", "psicologia", "vacunacion", "medicamento",
    ],
    "vivienda": [
        "arriendo", "alquiler", "hipoteca", "administracion", "renta",
        "predial", "ferreteria", "homecenter", "sodimac", "plomeria",
        "cerrajeria", "seguro hogar",
    ],
    "educacion": [
        "colegio", "universidad", "curso", "matricula", "udemy", "platzi",
        "libros", "libreria", "coursera", "pension colegio", "utiles",
        "idiomas", "certificacion",
    ],
    "ocio": [
        "netflix", "cine", "streaming", "spotify", "disney", "hbo", "steam",
        "bar", "concierto", "juego", "cinepolis", "cinemark", "playstation",
        "xbox", "gimnasio", "discoteca", "museo", "hotel", "cerveceria",
        "prime video", "youtube premium", "bowling",
    ],
    "servicios": [
        "luz", "agua", "internet", "gas", "celular", "energia", "claro",
        "movistar", "tigo", "entel", "wom", "basuras", "icloud", "microsoft",
        "antivirus", "hosting", "telefonia",
    ],
    # Va la ultima a proposito. "Recarga Tarjeta Metro" tiene que caer en
    # transporte y "Credito Hipotecario" en vivienda, y las dos se resuelven
    # antes de llegar aqui. Por eso tampoco hay un "tarjeta" suelto.
    "deudas": [
        "tarjeta de credito", "tarjeta credito", "avance tarjeta",
        "abono tarjeta", "minimo tarjeta", "manejo tarjeta",
        "intereses tarjeta", "mastercard", "prestamo", "credito libre",
        "credito de consumo", "credito personal", "cuota credito",
        "electrodomesticos",
    ],
}

#: Alta porque una coincidencia literal con un comercio conocido es mas fiable
#: que una prediccion dudosa del modelo.
CONFIANZA_KEYWORD = 0.90
CONFIANZA_SIN_MATCH = 0.40


def clasificar_por_reglas(descripcion: str) -> tuple[str, float]:
    """Devuelve (categoria, confianza) para una descripcion."""
    texto = normalizar_texto(descripcion)
    if not texto:
        return "otras", CONFIANZA_SIN_MATCH

    for categoria, palabras in KEYWORDS.items():
        if any(palabra in texto for palabra in palabras):
            return categoria, CONFIANZA_KEYWORD
    return "otras", CONFIANZA_SIN_MATCH
