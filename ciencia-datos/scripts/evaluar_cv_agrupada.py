"""Evalua el pipeline oficial del clasificador de gastos con CV agrupada por comercio.

Reutiliza sin modificar el pipeline de notebook.ipynb (secciones 8-9) pero, en
vez de una sola particion train/test, hace validacion cruzada de 5 folds con
sklearn.model_selection.StratifiedGroupKFold agrupando por "comercio" (para que
un mismo comercio nunca aparezca a la vez en train y test de un fold) y
estratificando por "categoria".

Para cada fold se entrena el pipeline en el train del fold y se evalua en el
test del fold (accuracy, f1_macro, f1_weighted, balanced_accuracy). Ademas se
guardan las predicciones out-of-fold (OOF): una fila por transaccion evaluada,
con la categoria real, la predicha y las probabilidades por clase, para que
las fases 3, 4 y 5 del roadmap las reutilicen tal cual sin volver a entrenar.

Uso:
    python ciencia-datos/scripts/evaluar_cv_agrupada.py \
        --datos ciencia-datos/datos/limpios/transacciones.csv \
        --salida ciencia-datos/experimentos/cv_agrupada_comercio.json \
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
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from features import CATEGORIAS  # noqa: E402

RAIZ_CIENCIA_DATOS = Path(__file__).resolve().parents[1]

#: Los pagos de deuda son gasto: el dinero sale igual que el del supermercado.
#: Mismo criterio que el notebook, o el clasificador se entrena y se evalua
#: sobre universos distintos.
TIPOS_DE_GASTO = ("egresos", "deudas")
DATOS_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "datos" / "limpios" / "transacciones.csv"
SALIDA_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "cv_agrupada_comercio.json"
OOF_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "oof_predicciones_cv.csv"
N_SPLITS = 5


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
        transacciones["tipo"].isin(TIPOS_DE_GASTO) & transacciones["categoria"].notna()
    ].copy()
    entrenables["descripcion_limpia"] = entrenables["descripcion_limpia"].fillna("")
    entrenables = entrenables[entrenables["descripcion_limpia"].str.len() > 0]
    return entrenables


def evaluar_cv_agrupada(entrenables: pd.DataFrame, semilla: int) -> tuple[list[dict], pd.DataFrame]:
    """Corre StratifiedGroupKFold(n_splits=5) agrupando por comercio.

    Devuelve (lista de resultados por fold, dataframe con las predicciones OOF
    concatenadas de los 5 folds).
    """
    X = entrenables["descripcion_limpia"].reset_index(drop=True)
    y = entrenables["categoria"].reset_index(drop=True)
    comercio = entrenables["comercio"].reset_index(drop=True)
    indice_original = entrenables.index.to_numpy()

    cv = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=semilla)

    resultados_por_fold: list[dict] = []
    filas_oof: list[pd.DataFrame] = []

    for fold, (idx_tr, idx_te) in enumerate(cv.split(X, y, groups=comercio)):
        comercios_train = set(comercio.iloc[idx_tr])
        comercios_test = set(comercio.iloc[idx_te])
        interseccion = comercios_train & comercios_test
        assert not interseccion, (
            f"Fold {fold}: {len(interseccion)} comercio(s) aparecen a la vez en "
            f"train y test ({sorted(interseccion)[:5]}...). "
            "La agrupacion por comercio se rompio."
        )

        X_tr, y_tr = X.iloc[idx_tr], y.iloc[idx_tr]
        X_te, y_te = X.iloc[idx_te], y.iloc[idx_te]

        inicio = time.time()
        clasificador = construir_clasificador(semilla)
        clasificador.fit(X_tr, y_tr)
        duracion = time.time() - inicio

        pred = clasificador.predict(X_te)
        proba = clasificador.predict_proba(X_te)
        clases = list(clasificador.classes_)
        # Reordena las columnas de probabilidad al orden fijo de CATEGORIAS
        # (features.CATEGORIAS), no al orden alfabetico que da classes_.
        #
        # Una categoria puede no estar en classes_: al agrupar por comercio,
        # todos los comercios de una categoria pequena pueden caer en test y el
        # modelo del fold no llega a verla. Se le da probabilidad 0 en lugar de
        # fallar, que es justo lo que mide este experimento: que le pasa al
        # clasificador ante algo que no vio.
        ausentes = [c for c in CATEGORIAS if c not in clases]
        if ausentes:
            print(f"  fold {fold}: sin ejemplos de entrenamiento para {ausentes}")
        proba_ordenada = np.zeros((len(pred), len(CATEGORIAS)), dtype=float)
        for j, cat in enumerate(CATEGORIAS):
            if cat in clases:
                proba_ordenada[:, j] = proba[:, clases.index(cat)]

        metricas = calcular_metricas(y_te, pred)
        resultados_por_fold.append({
            "fold": fold,
            "filas_train": int(len(idx_tr)),
            "filas_test": int(len(idx_te)),
            "comercios_train": len(comercios_train),
            "comercios_test": len(comercios_test),
            "tiempo_entrenamiento_seg": round(duracion, 2),
            "metricas": metricas,
        })

        fold_oof = pd.DataFrame({
            "indice_original": indice_original[idx_te],
            "comercio": comercio.iloc[idx_te].to_numpy(),
            "categoria_real": y_te.to_numpy(),
            "categoria_predicha": pred,
            "prob_max": proba_ordenada.max(axis=1),
        })
        for j, cat in enumerate(CATEGORIAS):
            fold_oof[f"prob_{cat}"] = proba_ordenada[:, j]
        fold_oof.insert(0, "fold", fold)
        filas_oof.append(fold_oof)

        print(
            f"Fold {fold}: train {len(idx_tr):,} | test {len(idx_te):,} | "
            f"comercios train {len(comercios_train)} / test {len(comercios_test)}"
        )
        for nombre, valor in metricas.items():
            print(f"  {nombre:<20} {valor:.4f}")

    oof = pd.concat(filas_oof, ignore_index=True)
    return resultados_por_fold, oof


def resumir_metricas(resultados_por_fold: list[dict]) -> dict[str, dict[str, float]]:
    nombres_metricas = resultados_por_fold[0]["metricas"].keys()
    resumen: dict[str, dict[str, float]] = {}
    for nombre in nombres_metricas:
        valores = np.array([r["metricas"][nombre] for r in resultados_por_fold])
        resumen[nombre] = {
            "media": float(valores.mean()),
            "desviacion_estandar": float(valores.std(ddof=0)),
        }
    return resumen


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evalua el pipeline oficial del clasificador de gastos (notebook "
            "secciones 8-9) con CV agrupada por comercio (StratifiedGroupKFold, 5 folds)."
        )
    )
    parser.add_argument("--datos", type=Path, default=Path(DATOS_POR_DEFECTO))
    parser.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO)
    parser.add_argument("--oof", type=Path, default=OOF_POR_DEFECTO)
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

    print(f"\n=== StratifiedGroupKFold(n_splits={N_SPLITS}) agrupado por comercio ===")
    resultados_por_fold, oof = evaluar_cv_agrupada(entrenables, args.semilla)

    resumen = resumir_metricas(resultados_por_fold)
    print("\n=== Media +/- desviacion estandar entre folds ===")
    for nombre, valores in resumen.items():
        print(f"  {nombre:<20} {valores['media']:.4f} +/- {valores['desviacion_estandar']:.4f}")

    args.oof.parent.mkdir(parents=True, exist_ok=True)
    oof.to_csv(args.oof, index=False, encoding="utf-8")
    print(f"\nOOF guardado en {args.oof} ({len(oof):,} filas)")

    salida = {
        "semilla": args.semilla,
        "dataset": str(args.datos),
        "filas_entrenables": int(len(entrenables)),
        "comercios_unicos": int(entrenables["comercio"].nunique()),
        "n_splits": N_SPLITS,
        "categorias": list(CATEGORIAS),
        "resultados_por_fold": resultados_por_fold,
        "resumen_metricas": resumen,
        "oof_predicciones_csv": str(args.oof),
    }

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with open(args.salida, "w", encoding="utf-8") as fh:
        json.dump(salida, fh, ensure_ascii=False, indent=2)

    print(f"\nGuardado en {args.salida}")


if __name__ == "__main__":
    main()
