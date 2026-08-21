"""Evalua el pipeline oficial del clasificador de gastos (notebook, secciones 8-9).

Reproduce, fuera del notebook, las dos particiones descritas en la seccion 8 y
el pipeline de la seccion 9, sin modificar ninguno de los dos, para dejar un
JSON con las metricas de referencia (baseline) versionado en el repo.

Uso:
    python ciencia-datos/scripts/evaluar_baseline.py \
        --datos ciencia-datos/datos/limpios/transacciones.csv \
        --salida ciencia-datos/experimentos/baseline_v1.json \
        --semilla 42
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

RAIZ_CIENCIA_DATOS = Path(__file__).resolve().parents[1]
DATOS_POR_DEFECTO = (
    "C:/Users/HardM/Desktop/Enterprise/hackaton-alura/G9-LATAM-TEAM-44-FinanceAI/"
    "ciencia-datos/datos/limpios/transacciones.csv"
)
SALIDA_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "baseline_v1.json"


def construir_vectorizador() -> FeatureUnion:
    """Igual que notebook.ipynb, seccion 9. No modificar."""
    return FeatureUnion([
        ("palabra", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
        ("caracter", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3, sublinear_tf=True)),
    ])


def construir_clasificador(semilla: int) -> Pipeline:
    """Igual que notebook.ipynb, seccion 9. No modificar."""
    return Pipeline([
        ("vectorizador", construir_vectorizador()),
        ("clf", CalibratedClassifierCV(LinearSVC(C=1.0, random_state=semilla), cv=3)),
    ])


def calcular_metricas(y_true, y_pred) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro")),
        "f1_weighted": float(f1_score(y_true, y_pred, average="weighted")),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
    }


def cargar_entrenables(ruta_datos: Path) -> pd.DataFrame:
    transacciones = pd.read_csv(ruta_datos)
    entrenables = transacciones[
        (transacciones["tipo"] == "egresos") & transacciones["categoria"].notna()
    ].copy()
    entrenables["descripcion_limpia"] = entrenables["descripcion_limpia"].fillna("")
    entrenables = entrenables[entrenables["descripcion_limpia"].str.len() > 0]
    return entrenables


def particion_aleatoria(entrenables: pd.DataFrame, semilla: int) -> dict:
    """Notebook seccion 8 (celda 29): aleatoria estratificada por categoria."""
    X_tr, X_te, y_tr, y_te = train_test_split(
        entrenables["descripcion_limpia"], entrenables["categoria"],
        test_size=0.25, random_state=semilla, stratify=entrenables["categoria"],
    )

    inicio = time.time()
    clasificador = construir_clasificador(semilla)
    clasificador.fit(X_tr, y_tr)
    duracion = time.time() - inicio

    pred = clasificador.predict(X_te)
    metricas = calcular_metricas(y_te, pred)

    return {
        "metricas": metricas,
        "filas_train": int(len(X_tr)),
        "filas_test": int(len(X_te)),
        "tiempo_entrenamiento_seg": round(duracion, 2),
    }


def particion_por_comercio(entrenables: pd.DataFrame, semilla: int) -> dict:
    """Notebook seccion 8 (celda 30) + seccion 10.2 (celda 39): comercios nunca vistos."""
    rng = np.random.RandomState(7)
    por_comercio = entrenables.groupby("comercio")["categoria"].first()

    comercios_test: list[str] = []
    for _, grupo in por_comercio.groupby(por_comercio):
        nombres = sorted(grupo.index)
        k = max(1, round(len(nombres) * 0.25))
        comercios_test += list(rng.choice(nombres, size=k, replace=False))
    comercios_test = set(comercios_test)

    mascara_test = entrenables["comercio"].isin(comercios_test)

    X_tr = entrenables.loc[~mascara_test, "descripcion_limpia"]
    y_tr = entrenables.loc[~mascara_test, "categoria"]
    X_te = entrenables.loc[mascara_test, "descripcion_limpia"]
    y_te = entrenables.loc[mascara_test, "categoria"]

    inicio = time.time()
    clasificador = construir_clasificador(semilla)
    clasificador.fit(X_tr, y_tr)
    duracion = time.time() - inicio

    pred = clasificador.predict(X_te)
    metricas = calcular_metricas(y_te, pred)

    return {
        "metricas": metricas,
        "filas_train": int(len(X_tr)),
        "filas_test": int(len(X_te)),
        "comercios_totales": int(por_comercio.size),
        "comercios_reservados": len(comercios_test),
        "tiempo_entrenamiento_seg": round(duracion, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evalua el baseline oficial del clasificador de gastos (notebook secciones 8-9)."
    )
    parser.add_argument("--datos", type=Path, default=Path(DATOS_POR_DEFECTO))
    parser.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO)
    parser.add_argument("--semilla", type=int, default=42)
    args = parser.parse_args()

    if not args.datos.exists():
        print(f"No existe el dataset: {args.datos}", file=sys.stderr)
        sys.exit(1)

    entrenables = cargar_entrenables(args.datos)
    print(
        f"{len(entrenables):,} egresos etiquetados | "
        f"{entrenables['comercio'].nunique()} comercios unicos"
    )

    print("\n=== Particion aleatoria estratificada (comercios conocidos) ===")
    resultado_aleatorio = particion_aleatoria(entrenables, args.semilla)
    print(f"train {resultado_aleatorio['filas_train']:,} | test {resultado_aleatorio['filas_test']:,}")
    for nombre, valor in resultado_aleatorio["metricas"].items():
        print(f"  {nombre:<20} {valor:.4f}")

    print("\n=== Particion por comercio (comercios nunca vistos) ===")
    resultado_comercio = particion_por_comercio(entrenables, args.semilla)
    print(
        f"comercios reservados: {resultado_comercio['comercios_reservados']}"
        f"/{resultado_comercio['comercios_totales']}"
    )
    print(f"train {resultado_comercio['filas_train']:,} | test {resultado_comercio['filas_test']:,}")
    for nombre, valor in resultado_comercio["metricas"].items():
        print(f"  {nombre:<20} {valor:.4f}")

    salida = {
        "semilla": args.semilla,
        "dataset": str(args.datos),
        "filas_entrenables": int(len(entrenables)),
        "comercios_unicos": int(entrenables["comercio"].nunique()),
        "particion_aleatoria": resultado_aleatorio,
        "particion_por_comercio": resultado_comercio,
    }

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with open(args.salida, "w", encoding="utf-8") as fh:
        json.dump(salida, fh, ensure_ascii=False, indent=2)

    print(f"\nGuardado en {args.salida}")


if __name__ == "__main__":
    main()
