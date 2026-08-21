"""Benchmark de modelos clasicos de clasificacion de gastos (Fase 9).

Compara, sobre exactamente el mismo split (StratifiedGroupKFold(n_splits=5,
shuffle=True, random_state=42) agrupando por "comercio", igual que la Fase 2
en ciencia-datos/scripts/evaluar_cv_agrupada.py), varios candidatos de
vectorizador + clasificador, todos sobre la columna "descripcion_limpia":

1. actual (palabra+caracter TFIDF) + LinearSVC calibrado -- el pipeline
   vigente del notebook (seccion 9). Sirve de control: debe salir igual o muy
   cercano a ciencia-datos/experimentos/cv_agrupada_comercio.json (Fase 2).
2. palabra+caracter TFIDF + LogisticRegression
3. solo palabra TFIDF (1,2-gram) + LinearSVC calibrado
4. solo caracter TFIDF (char_wb 3-5) + LinearSVC calibrado
5. palabra+caracter TFIDF + MultinomialNB o ComplementNB (se corren ambos y
   se documenta cual se usa para el CSV final, ver salida en consola y el .md)

Uso:
    python ciencia-datos/scripts/benchmark_clasico.py \
        --datos ciencia-datos/datos/limpios/transacciones.csv \
        --salida ciencia-datos/experimentos/benchmark_clasico.csv
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.naive_bayes import ComplementNB, MultinomialNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

RAIZ_CIENCIA_DATOS = Path(__file__).resolve().parents[1]
DATOS_POR_DEFECTO = (
    "C:/Users/HardM/Desktop/Enterprise/hackaton-alura/G9-LATAM-TEAM-44-FinanceAI/"
    "ciencia-datos/datos/limpios/transacciones.csv"
)
SALIDA_CSV_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "benchmark_clasico.csv"
SALIDA_MD_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "benchmark_clasico.md"
N_SPLITS = 5
SEMILLA = 42


# ------------------------------------------------------------- vectorizadores

def vectorizador_palabra() -> TfidfVectorizer:
    return TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)


def vectorizador_caracter() -> TfidfVectorizer:
    return TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3, sublinear_tf=True)


def vectorizador_completo() -> FeatureUnion:
    """Igual que notebook.ipynb, seccion 9 / evaluar_cv_agrupada.py. No modificar."""
    return FeatureUnion([
        ("palabra", vectorizador_palabra()),
        ("caracter", vectorizador_caracter()),
    ])


# ---------------------------------------------------------------- candidatos

def pipeline_actual_svc_calibrado(semilla: int) -> Pipeline:
    return Pipeline([
        ("vectorizador", vectorizador_completo()),
        ("clf", CalibratedClassifierCV(LinearSVC(C=1.0, random_state=semilla), cv=3)),
    ])


def pipeline_logreg(semilla: int) -> Pipeline:
    return Pipeline([
        ("vectorizador", vectorizador_completo()),
        ("clf", LogisticRegression(max_iter=1000, random_state=semilla)),
    ])


def pipeline_solo_palabra_svc_calibrado(semilla: int) -> Pipeline:
    return Pipeline([
        ("vectorizador", vectorizador_palabra()),
        ("clf", CalibratedClassifierCV(LinearSVC(C=1.0, random_state=semilla), cv=3)),
    ])


def pipeline_solo_caracter_svc_calibrado(semilla: int) -> Pipeline:
    return Pipeline([
        ("vectorizador", vectorizador_caracter()),
        ("clf", CalibratedClassifierCV(LinearSVC(C=1.0, random_state=semilla), cv=3)),
    ])


def pipeline_multinomial_nb(semilla: int) -> Pipeline:
    return Pipeline([
        ("vectorizador", vectorizador_completo()),
        ("clf", MultinomialNB()),
    ])


def pipeline_complement_nb(semilla: int) -> Pipeline:
    return Pipeline([
        ("vectorizador", vectorizador_completo()),
        ("clf", ComplementNB()),
    ])


# ------------------------------------------------------------------- metrica

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


def evaluar_candidato(
    nombre: str,
    construir_pipeline: Callable[[int], Pipeline],
    X: pd.Series,
    y: pd.Series,
    comercio: pd.Series,
    semilla: int,
) -> dict:
    """Corre StratifiedGroupKFold(n_splits=5) agrupando por comercio para un candidato."""
    cv = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=semilla)

    metricas_por_fold: list[dict[str, float]] = []
    tiempos: list[float] = []

    print(f"\n=== {nombre} ===")
    for fold, (idx_tr, idx_te) in enumerate(cv.split(X, y, groups=comercio)):
        comercios_train = set(comercio.iloc[idx_tr])
        comercios_test = set(comercio.iloc[idx_te])
        interseccion = comercios_train & comercios_test
        assert not interseccion, (
            f"Fold {fold}: {len(interseccion)} comercio(s) aparecen a la vez en "
            f"train y test. La agrupacion por comercio se rompio."
        )

        X_tr, y_tr = X.iloc[idx_tr], y.iloc[idx_tr]
        X_te, y_te = X.iloc[idx_te], y.iloc[idx_te]

        inicio = time.time()
        clasificador = construir_pipeline(semilla)
        clasificador.fit(X_tr, y_tr)
        duracion = time.time() - inicio
        tiempos.append(duracion)

        pred = clasificador.predict(X_te)
        metricas = calcular_metricas(y_te, pred)
        metricas_por_fold.append(metricas)

        print(
            f"  Fold {fold}: train {len(idx_tr):,} | test {len(idx_te):,} | "
            f"tiempo {duracion:.1f}s | "
            + " | ".join(f"{k}={v:.4f}" for k, v in metricas.items())
        )

    resumen: dict[str, tuple[float, float]] = {}
    for nombre_metrica in metricas_por_fold[0].keys():
        valores = np.array([m[nombre_metrica] for m in metricas_por_fold])
        resumen[nombre_metrica] = (float(valores.mean()), float(valores.std(ddof=0)))

    print(
        f"  Resumen: "
        + " | ".join(f"{k}={v[0]:.4f}+/-{v[1]:.4f}" for k, v in resumen.items())
        + f" | tiempo_total={sum(tiempos):.1f}s"
    )

    return {
        "modelo": nombre,
        "resumen": resumen,
        "tiempo_total_seg": sum(tiempos),
    }


def formatear_media_std(resumen: dict[str, tuple[float, float]], nombre_metrica: str) -> str:
    media, std = resumen[nombre_metrica]
    return f"{media:.4f} +/- {std:.4f}"


def tabla_markdown(tabla: pd.DataFrame) -> str:
    """Tabla markdown simple, sin depender del paquete opcional 'tabulate'."""
    columnas = list(tabla.columns)
    encabezado = "| " + " | ".join(columnas) + " |"
    separador = "| " + " | ".join("---" for _ in columnas) + " |"
    filas = [
        "| " + " | ".join(str(valor) for valor in fila) + " |"
        for fila in tabla.itertuples(index=False, name=None)
    ]
    return "\n".join([encabezado, separador, *filas])


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark de vectorizadores/clasificadores clasicos sobre el mismo "
            "split StratifiedGroupKFold agrupado por comercio que la Fase 2."
        )
    )
    parser.add_argument("--datos", type=Path, default=Path(DATOS_POR_DEFECTO))
    parser.add_argument("--salida", type=Path, default=SALIDA_CSV_POR_DEFECTO)
    parser.add_argument("--salida-md", type=Path, default=SALIDA_MD_POR_DEFECTO)
    parser.add_argument("--semilla", type=int, default=SEMILLA)
    args = parser.parse_args()

    if not args.datos.exists():
        print(f"No existe el dataset: {args.datos}", file=sys.stderr)
        sys.exit(1)

    entrenables = cargar_entrenables(args.datos)
    print(
        f"{len(entrenables):,} egresos etiquetados | "
        f"{entrenables['comercio'].nunique()} comercios unicos"
    )

    X = entrenables["descripcion_limpia"].reset_index(drop=True)
    y = entrenables["categoria"].reset_index(drop=True)
    comercio = entrenables["comercio"].reset_index(drop=True)

    # Los candidatos 1-4 son fijos. El candidato 5 (Naive Bayes) se decide
    # entre MultinomialNB y ComplementNB corriendo ambos y quedandonos con el
    # de mejor f1_macro medio (se documenta la comparacion en el .md).
    resultado_multinomial = evaluar_candidato(
        "palabra+caracter TFIDF + MultinomialNB",
        pipeline_multinomial_nb,
        X, y, comercio, args.semilla,
    )
    resultado_complement = evaluar_candidato(
        "palabra+caracter TFIDF + ComplementNB",
        pipeline_complement_nb,
        X, y, comercio, args.semilla,
    )
    if resultado_complement["resumen"]["f1_macro"][0] >= resultado_multinomial["resumen"]["f1_macro"][0]:
        resultado_nb = resultado_complement
        nb_elegido, nb_descartado = "ComplementNB", "MultinomialNB"
    else:
        resultado_nb = resultado_multinomial
        nb_elegido, nb_descartado = "MultinomialNB", "ComplementNB"
    resultado_nb = dict(resultado_nb)
    resultado_nb["modelo"] = "palabra+caracter TFIDF + Naive Bayes (mejor de MultinomialNB/ComplementNB)"

    resultados = [
        evaluar_candidato(
            "actual (palabra+caracter TFIDF) + LinearSVC calibrado",
            pipeline_actual_svc_calibrado,
            X, y, comercio, args.semilla,
        ),
        evaluar_candidato(
            "palabra+caracter TFIDF + LogisticRegression",
            pipeline_logreg,
            X, y, comercio, args.semilla,
        ),
        evaluar_candidato(
            "solo palabra TFIDF (1,2-gram) + LinearSVC calibrado",
            pipeline_solo_palabra_svc_calibrado,
            X, y, comercio, args.semilla,
        ),
        evaluar_candidato(
            "solo caracter TFIDF (char_wb 3-5) + LinearSVC calibrado",
            pipeline_solo_caracter_svc_calibrado,
            X, y, comercio, args.semilla,
        ),
        resultado_nb,
    ]

    resultados.sort(key=lambda r: r["resumen"]["f1_macro"][0], reverse=True)

    filas = []
    for r in resultados:
        resumen = r["resumen"]
        filas.append({
            "modelo": r["modelo"],
            "accuracy": formatear_media_std(resumen, "accuracy"),
            "f1_macro": formatear_media_std(resumen, "f1_macro"),
            "f1_weighted": formatear_media_std(resumen, "f1_weighted"),
            "balanced_accuracy": formatear_media_std(resumen, "balanced_accuracy"),
        })
    tabla = pd.DataFrame(filas)

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(args.salida, index=False, encoding="utf-8")
    print(f"\nGuardado CSV en {args.salida}")

    # ------------------------------------------------------------------ .md
    lineas_nb = (
        f"- Naive Bayes: se probaron **MultinomialNB** "
        f"(f1_macro = {formatear_media_std(resultado_multinomial['resumen'], 'f1_macro')}) "
        f"y **ComplementNB** "
        f"(f1_macro = {formatear_media_std(resultado_complement['resumen'], 'f1_macro')}). "
        f"Se eligio **{nb_elegido}** para la fila del benchmark (descartando {nb_descartado}) "
        f"porque obtuvo el f1_macro medio mas alto de los dos."
    )

    mejor = resultados[0]
    f1_mejor = mejor["resumen"]["f1_macro"]
    equivalentes = []
    for r in resultados[1:]:
        f1_otro = r["resumen"]["f1_macro"]
        # Se consideran equivalentes si sus intervalos [media-std, media+std] se solapan
        # con el del mejor (heuristica simple de "dentro de la desviacion estandar").
        solapa = (f1_mejor[0] - f1_mejor[1]) <= (f1_otro[0] + f1_otro[1]) and \
                 (f1_otro[0] - f1_otro[1]) <= (f1_mejor[0] + f1_mejor[1])
        if solapa:
            equivalentes.append(r["modelo"])

    if equivalentes:
        texto_equivalencia = (
            f"El mejor por f1_macro medio (**{mejor['modelo']}**, "
            f"f1_macro = {formatear_media_std(mejor['resumen'], 'f1_macro')}) no se distingue "
            f"con confianza de: " + "; ".join(equivalentes) + ". Sus rangos "
            "media +/- desviacion estandar de f1_macro se solapan con el del primero, "
            "por lo que son estadisticamente equivalentes en este benchmark; la diferencia "
            "observada podria deberse a la variabilidad entre folds y no a una ventaja real "
            "de un modelo sobre otro."
        )
    else:
        texto_equivalencia = (
            f"El mejor por f1_macro medio es **{mejor['modelo']}** "
            f"(f1_macro = {formatear_media_std(mejor['resumen'], 'f1_macro')}), y su rango "
            "media +/- desviacion estandar no se solapa con el de ningun otro candidato, por lo "
            "que la diferencia frente al resto parece real y no solo ruido entre folds."
        )

    control = resultados_por_nombre = {r["modelo"]: r for r in resultados}
    actual = control["actual (palabra+caracter TFIDF) + LinearSVC calibrado"]

    md = f"""# Benchmark de modelos clasicos (Fase 9)

Dataset: `{args.datos}`
Filas entrenables: {len(entrenables):,} | Comercios unicos: {entrenables['comercio'].nunique()}
Split: `StratifiedGroupKFold(n_splits={N_SPLITS}, shuffle=True, random_state={args.semilla})`
agrupado por `comercio`, estratificado por `categoria` (igual que la Fase 2,
`ciencia-datos/scripts/evaluar_cv_agrupada.py`).

## Resultados (ordenados por f1_macro medio, de mejor a peor)

{tabla_markdown(tabla)}

## Control de reproducibilidad del split

El candidato 1 ("actual") es el mismo pipeline evaluado en la Fase 2
(`ciencia-datos/experimentos/cv_agrupada_comercio.json`). Aqui salio
accuracy = {formatear_media_std(actual['resumen'], 'accuracy')},
f1_macro = {formatear_media_std(actual['resumen'], 'f1_macro')},
f1_weighted = {formatear_media_std(actual['resumen'], 'f1_weighted')},
balanced_accuracy = {formatear_media_std(actual['resumen'], 'balanced_accuracy')}.
Comparar estos numeros contra el JSON de la Fase 2 confirma (o no) que el split
de StratifiedGroupKFold se reprodujo exactamente igual.

## Naive Bayes: MultinomialNB vs ComplementNB

{lineas_nb}

## Conclusion

{texto_equivalencia}

Recomendacion: mantener el pipeline actual (palabra+caracter TFIDF + LinearSVC
calibrado) salvo que la diferencia frente a otro candidato sea, ademas de
mayor en la media, mayor que la suma de ambas desviaciones estandar (es decir,
una diferencia que no se explique por la variabilidad entre folds). Cuando dos
candidatos son estadisticamente equivalentes en f1_macro, conviene preferir el
mas simple o el mas rapido de entrenar, no el que tenga la cifra ligeramente
mas alta.
"""

    args.salida_md.parent.mkdir(parents=True, exist_ok=True)
    with open(args.salida_md, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"Guardado MD en {args.salida_md}")


if __name__ == "__main__":
    main()
