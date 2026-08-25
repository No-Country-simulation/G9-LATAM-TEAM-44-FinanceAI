"""Limpieza y consolidacion de los extractos crudos.

Toma los archivos que produce `generador_usuarios.py` (json, csv y xlsx
mezclados, fechas en tres formatos, descripciones nulas, montos negativos) y
devuelve una sola tabla tipada.

Se usa como modulo desde el notebook o como script:

    python ciencia-datos/scripts/limpieza_datos.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

# La normalizacion de texto vive en features.py, un nivel arriba.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from features import normalizar_categoria, normalizar_texto  # noqa: E402

COLUMNAS = ["fecha", "tipo", "descripcion", "monto", "categoria", "comercio"]

#: Centinela para las fechas irrecuperables. Un NaT desapareceria en la primera
#: agregacion; asi se ven en el EDA y se pueden contar.
FECHA_CENTINELA = pd.Timestamp("1900-01-01")


def leer_extracto(ruta: str) -> pd.DataFrame:
    """Lee un extracto sea cual sea su formato y devuelve siempre las mismas columnas."""
    extension = os.path.splitext(ruta)[1].lower()

    if extension == ".json":
        with open(ruta, "r", encoding="utf-8") as f:
            df = pd.DataFrame(json.load(f))
    elif extension == ".csv":
        df = pd.read_csv(ruta, encoding="utf-8-sig")
    elif extension == ".xlsx":
        df = pd.read_excel(ruta)
    else:
        raise ValueError(f"Formato no soportado: {ruta}")

    for columna in COLUMNAS:
        if columna not in df.columns:
            df[columna] = None
    return df[COLUMNAS]


#: Formatos que emite el generador, en orden de prioridad.
FORMATOS_FECHA = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d")


def limpiar_fechas(serie: pd.Series) -> pd.Series:
    """Unifica %Y-%m-%d, %d/%m/%Y y %Y/%m/%d a datetime.

    Se prueba formato por formato. `format='mixed'` con `dayfirst=True` parece
    equivalente pero ante '2026/03/05' aplica igualmente dayfirst y devuelve el
    3 de mayo, con lo que aparecen meses que no estan en el dataset.

    Cada formato se aplica solo a lo que sigue sin parsear, asi que el orden de
    FORMATOS_FECHA resuelve los empates.
    """
    texto = serie.astype("string").str.strip()
    resultado = pd.Series(pd.NaT, index=serie.index, dtype="datetime64[ns]")

    for formato in FORMATOS_FECHA:
        pendientes = resultado.isna() & texto.notna()
        if not pendientes.any():
            break
        intento = pd.to_datetime(texto[pendientes], format=formato, errors="coerce")
        resultado[pendientes] = intento

    return resultado.fillna(FECHA_CENTINELA)


def limpiar_montos(serie: pd.Series) -> pd.Series:
    """Convierte a numero y toma el valor absoluto.

    El sentido del movimiento ya lo da la columna `tipo`. Un negativo colandose
    en la agregacion restaria del total de su categoria.
    """
    return pd.to_numeric(serie, errors="coerce").fillna(0.0).abs()


def limpiar_extracto(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica la limpieza completa a un extracto y anade `descripcion_limpia`."""
    limpio = df.copy()
    limpio["fecha"] = limpiar_fechas(limpio["fecha"])
    limpio["monto"] = limpiar_montos(limpio["monto"])
    limpio["tipo"] = limpio["tipo"].astype("string").str.strip().str.lower()
    limpio["descripcion"] = limpio["descripcion"].astype("string")
    limpio["descripcion_limpia"] = limpio["descripcion"].map(normalizar_texto)

    # Solo los egresos llevan categoria; el clasificador se entrena con gastos.
    limpio["categoria"] = limpio["categoria"].where(
        limpio["categoria"].notna(), None
    ).map(lambda v: normalizar_categoria(v) if v is not None and str(v) != "nan" else None)

    return limpio.sort_values("fecha").reset_index(drop=True)


def consolidar(carpeta_entrada: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apila todos los extractos de la carpeta en una sola tabla.

    Returns:
        (transacciones, usuarios), limpios y con `usuario_id` en ambos.
    """
    ruta_usuarios = os.path.join(carpeta_entrada, "usuarios.csv")
    if not os.path.exists(ruta_usuarios):
        raise FileNotFoundError(
            f"No existe {ruta_usuarios}. Ejecuta primero generador_usuarios.py."
        )
    usuarios = pd.read_csv(ruta_usuarios, encoding="utf-8")
    usuarios["usuario_id"] = usuarios["usuario_id"].astype(str).str.zfill(3)

    partes: list[pd.DataFrame] = []
    for _, fila in usuarios.iterrows():
        ruta = os.path.join(carpeta_entrada, fila["archivo"])
        if not os.path.exists(ruta):
            print(f"  aviso: falta {fila['archivo']}, se omite")
            continue
        parte = limpiar_extracto(leer_extracto(ruta))
        parte.insert(0, "usuario_id", fila["usuario_id"])
        partes.append(parte)

    if not partes:
        raise RuntimeError("No se pudo leer ningun extracto.")

    transacciones = pd.concat(partes, ignore_index=True)
    return transacciones, usuarios


def main() -> None:
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "datos"))
    parser = argparse.ArgumentParser(description="Limpia y consolida los extractos crudos.")
    parser.add_argument("--entrada", default=os.path.join(base, "crudos"))
    parser.add_argument("--salida", default=os.path.join(base, "limpios"))
    args = parser.parse_args()

    os.makedirs(args.salida, exist_ok=True)
    print(f"Leyendo extractos de {args.entrada} ...")
    transacciones, usuarios = consolidar(args.entrada)

    ruta_tx = os.path.join(args.salida, "transacciones.csv")
    ruta_us = os.path.join(args.salida, "usuarios.csv")
    transacciones.to_csv(ruta_tx, index=False, encoding="utf-8")
    usuarios.to_csv(ruta_us, index=False, encoding="utf-8")

    egresos = transacciones[transacciones["tipo"].isin(("egresos", "deudas"))]
    print(f"  {len(transacciones):,} transacciones -> {ruta_tx}")
    print(f"  {len(usuarios):,} usuarios        -> {ruta_us}")
    print(f"  egresos etiquetados: {egresos['categoria'].notna().sum():,}")
    print(f"  descripciones vacias tras limpiar: {(transacciones['descripcion_limpia'] == '').sum():,}")


if __name__ == "__main__":
    main()
