"""Ejecuta los ejemplos documentados contra la API.

Prueba de humo end-to-end del backend, el ml-service y los artefactos.

    python docs/ejemplos.py                      # contra localhost:8080
    python docs/ejemplos.py http://mi-host:8080  # contra otro despliegue

Solo biblioteca estandar, no hace falta instalar nada.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/") + "/api/v1"

EJEMPLOS = [
    ("1 · Usuario con finanzas sanas", "/analisis-financiero", {
        "ingreso_mensual": 4500, "nivel_endeudamiento": 12, "frecuencia_ahorro": "Alta",
        "transacciones": [
            {"descripcion": "Supermercado Exito", "valor": 420},
            {"descripcion": "Gasolinera Terpel", "valor": 180},
            {"descripcion": "Netflix Streaming", "valor": 40},
            {"descripcion": "Arriendo Apartamento", "valor": 900},
        ]}, 200, "Saludable"),

    ("2 · Usuario en observación", "/analisis-financiero", {
        "ingreso_mensual": 3000, "nivel_endeudamiento": 40, "frecuencia_ahorro": "Baja",
        "transacciones": [
            {"descripcion": "TRF/POS Supermercado Jumbo REF993021", "valor": 620},
            {"descripcion": "Uber Trip BOGOTA", "valor": 240},
            {"descripcion": "Cinepolis Entradas", "valor": 180},
            {"descripcion": "Arriendo Apartamento", "valor": 1100},
            {"descripcion": "Farmacia San Pablo", "valor": 130},
            {"descripcion": "PAGO TARJETA DE CREDITO", "valor": 260},
        ]}, 200, "En observación"),

    ("3 · Usuario en riesgo", "/analisis-financiero", {
        "ingreso_mensual": 2200, "nivel_endeudamiento": 65, "frecuencia_ahorro": "Nula",
        "transacciones": [
            {"descripcion": "### supermercado ara", "valor": 700},
            {"descripcion": "Bar El Callejon", "valor": 380},
            {"descripcion": "Steam Games", "valor": 210},
            {"descripcion": "Cuota Hipoteca Vivienda", "valor": 1200},
            {"descripcion": "Gasolinera Pemx", "valor": 260},
        ]}, 200, "En riesgo"),

    ("4 · Pagos de tarjeta y cuotas", "/analisis-financiero", {
        "ingreso_mensual": 3200, "nivel_endeudamiento": 30, "frecuencia_ahorro": "Baja",
        "transacciones": [
            {"descripcion": "PAGO TARJETA DE CREDITO", "valor": 480},
            {"descripcion": "Cuota Prestamo Bancario", "valor": 350},
            {"descripcion": "Cuota de Manejo Tarjeta", "valor": 25},
            {"descripcion": "Arriendo Apartamento", "valor": 850},
            {"descripcion": "Supermercado Exito", "valor": 390},
            {"descripcion": "Recarga Tarjeta Metro", "valor": 60},
        ]}, 200, None),

    ("5 · Clasificación aislada", "/clasificar-transacciones", {
        "transacciones": [
            {"descripcion": "Supermercado Exito", "valor": 420},
            {"descripcion": "TRF/POS Gasolinera Terpel REF88213", "valor": 300},
            {"descripcion": "Netflix Streaming", "valor": 40},
            {"descripcion": "### farmacia cruz verde", "valor": 85},
            {"descripcion": "Avance Tarjeta de Credito", "valor": 300},
            {"descripcion": "zxqw plfj mmnb", "valor": 25},
        ]}, 200, None),

    ("6 · Validación de entrada", "/analisis-financiero", {
        "ingreso_mensual": 0, "nivel_endeudamiento": 150,
        "frecuencia_ahorro": "Siempre", "transacciones": [],
    }, 400, None),
]


def post(ruta: str, cuerpo: dict) -> tuple[int, dict]:
    peticion = urllib.request.Request(
        BASE + ruta, data=json.dumps(cuerpo).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            return respuesta.status, json.loads(respuesta.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def main() -> int:
    print(f"API: {BASE}\n")
    try:
        with urllib.request.urlopen(BASE + "/ml-status", timeout=10) as r:
            estado = json.loads(r.read())
        modelo = estado.get("modelo") or {}
        print(f"ml-service: {estado.get('modo')} | modelo {modelo.get('version', '?')} "
              f"(origen: {modelo.get('origen', '?')})\n")
    except Exception as e:
        print(f"No se pudo consultar /ml-status: {e}")
        print("¿Está levantada la API? -> docker compose up\n")
        return 1

    fallos = 0
    for titulo, ruta, cuerpo, esperado, perfil_esperado in EJEMPLOS:
        codigo, datos = post(ruta, cuerpo)

        ok = codigo == esperado
        if ok and perfil_esperado:
            ok = datos.get("perfil_financiero") == perfil_esperado

        marca = "OK " if ok else "FALLO"
        if not ok:
            fallos += 1

        print("=" * 74)
        print(f"[{marca}] {titulo}  ->  POST {ruta}  [{codigo}]")
        print("=" * 74)
        print(json.dumps(datos, indent=2, ensure_ascii=False))
        print()

    print("=" * 74)
    if fallos:
        print(f"{fallos} de {len(EJEMPLOS)} ejemplos no dieron el resultado esperado.")
    else:
        print(f"Los {len(EJEMPLOS)} ejemplos se comportaron como está documentado.")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
