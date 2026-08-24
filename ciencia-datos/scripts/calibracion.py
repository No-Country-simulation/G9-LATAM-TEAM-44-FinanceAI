"""Calibracion y umbral de confianza sobre las predicciones OOF de la Fase 2.

No reentrena nada: lee ciencia-datos/experimentos/oof_predicciones_cv.csv
(generado por evaluar_cv_agrupada.py con StratifiedGroupKFold agrupado por
comercio; cada prediccion fue hecha por un modelo que nunca vio ese comercio
en entrenamiento, es decir, out-of-distribution/OOD relativo a ese fold) y
calcula:

1. Coverage vs accuracy: para cada umbral de `prob_max` en
   [0.0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9], que fraccion de filas queda por encima
   del umbral (coverage) y que accuracy tienen las aceptadas.
2. Curva de calibracion (reliability diagram): 10 bins de `prob_max` entre 0 y
   1, con la accuracy real observada en cada bin vs. la confianza media del
   bin.
3. Brier score multiclase: promedio sobre las 8 columnas de probabilidad de
   (prob_asignada_a_cada_clase - indicador_clase_real)^2.
4. Expected Calibration Error (ECE): promedio ponderado (por soporte) de
   |accuracy_bin - confianza_media_bin| sobre los bins del punto 2.

Guarda:
- ciencia-datos/experimentos/calibracion.json: todas las cifras anteriores.
- ciencia-datos/experimentos/calibracion_reliability.png: curva de
  calibracion (confianza media del bin vs. accuracy observada) contra la
  diagonal ideal.
- ciencia-datos/experimentos/calibracion_coverage_accuracy.png: coverage y
  accuracy de las aceptadas en funcion del umbral.

Uso:
    python ciencia-datos/scripts/calibracion.py \
        --oof ciencia-datos/experimentos/oof_predicciones_cv.csv \
        --salida-json ciencia-datos/experimentos/calibracion.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from features import CATEGORIAS  # noqa: E402

RAIZ_CIENCIA_DATOS = Path(__file__).resolve().parents[1]
OOF_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "oof_predicciones_cv.csv"
SALIDA_JSON_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "calibracion.json"
SALIDA_RELIABILITY_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "calibracion_reliability.png"
SALIDA_COVERAGE_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "calibracion_coverage_accuracy.png"

UMBRALES = [0.0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9]
N_BINS = 10


def cargar_oof(ruta: Path) -> pd.DataFrame:
    oof = pd.read_csv(ruta)
    columnas_requeridas = {"categoria_real", "categoria_predicha", "prob_max"} | {
        f"prob_{c}" for c in CATEGORIAS
    }
    faltantes = columnas_requeridas - set(oof.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas en {ruta}: {faltantes}")
    oof = oof.copy()
    oof["si_correcta"] = oof["categoria_real"] == oof["categoria_predicha"]
    return oof


def coverage_vs_accuracy(oof: pd.DataFrame, umbrales: list[float]) -> list[dict]:
    """Para cada umbral: fraccion de filas aceptadas (coverage) y su accuracy."""
    total = len(oof)
    resultados = []
    for umbral in umbrales:
        aceptadas = oof[oof["prob_max"] >= umbral]
        coverage = len(aceptadas) / total if total else 0.0
        accuracy = float(aceptadas["si_correcta"].mean()) if len(aceptadas) else None
        resultados.append({
            "umbral": umbral,
            "coverage": coverage,
            "filas_aceptadas": int(len(aceptadas)),
            "accuracy_aceptadas": accuracy,
        })
    return resultados


def curva_calibracion(oof: pd.DataFrame, n_bins: int) -> list[dict]:
    """Bins de ancho fijo sobre prob_max en [0, 1].

    Para cada bin: confianza media (media de prob_max en el bin) y accuracy
    real observada (fraccion de si_correcta en el bin).
    """
    bordes = np.linspace(0.0, 1.0, n_bins + 1)
    # Ultimo bin es cerrado por ambos lados; el resto, cerrado por la derecha.
    indices_bin = np.digitize(oof["prob_max"], bordes[1:-1], right=True)

    bins = []
    for i in range(n_bins):
        en_bin = oof[indices_bin == i]
        soporte = int(len(en_bin))
        confianza_media = float(en_bin["prob_max"].mean()) if soporte else None
        accuracy_bin = float(en_bin["si_correcta"].mean()) if soporte else None
        bins.append({
            "bin": i,
            "rango": [float(bordes[i]), float(bordes[i + 1])],
            "soporte": soporte,
            "confianza_media": confianza_media,
            "accuracy_observada": accuracy_bin,
        })
    return bins


def expected_calibration_error(bins: list[dict], total: int) -> float:
    """ECE = suma ponderada por soporte de |accuracy_bin - confianza_media_bin|."""
    if total == 0:
        return 0.0
    ece = 0.0
    for b in bins:
        if b["soporte"] == 0:
            continue
        ece += (b["soporte"] / total) * abs(b["accuracy_observada"] - b["confianza_media"])
    return float(ece)


def brier_score_multiclase(oof: pd.DataFrame) -> float:
    """Brier score multiclase promediado sobre las 8 clases y todas las filas.

    Para cada fila y cada clase c: (prob_c - 1{categoria_real == c})^2.
    Se promedia sobre las 8 clases y luego sobre todas las filas (equivalente
    a promediar sobre las 8*N celdas).
    """
    columnas_prob = [f"prob_{c}" for c in CATEGORIAS]
    probs = oof[columnas_prob].to_numpy()
    indicador = np.zeros_like(probs)
    for j, categoria in enumerate(CATEGORIAS):
        indicador[:, j] = (oof["categoria_real"] == categoria).to_numpy()
    return float(np.mean((probs - indicador) ** 2))


def graficar_reliability(bins: list[dict], ece: float, ruta: Path) -> None:
    confianzas = [b["confianza_media"] for b in bins if b["soporte"] > 0]
    accuracies = [b["accuracy_observada"] for b in bins if b["soporte"] > 0]
    soportes = [b["soporte"] for b in bins if b["soporte"] > 0]

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Calibracion ideal")
    ax.scatter(confianzas, accuracies, s=[max(20, s / 20) for s in soportes], color="C0", zorder=3)
    ax.plot(confianzas, accuracies, color="C0", alpha=0.6, label="Observado (OOD)")
    ax.set_xlabel("Confianza media del bin (prob_max)")
    ax.set_ylabel("Accuracy observada en el bin")
    ax.set_title(f"Curva de calibracion sobre predicciones OOD\nECE = {ece:.4f}")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend()
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


def graficar_coverage_accuracy(resultados: list[dict], ruta: Path) -> None:
    umbrales = [r["umbral"] for r in resultados]
    coverage = [r["coverage"] for r in resultados]
    accuracy = [r["accuracy_aceptadas"] if r["accuracy_aceptadas"] is not None else np.nan for r in resultados]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(umbrales, coverage, marker="o", label="Coverage (fraccion aceptada)")
    ax.plot(umbrales, accuracy, marker="s", label="Accuracy de las aceptadas")
    ax.set_xlabel("Umbral de confianza (prob_max)")
    ax.set_ylabel("Fraccion")
    ax.set_title("Coverage vs. accuracy sobre predicciones OOD")
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Calibracion (reliability diagram, ECE, Brier) y umbral de confianza "
            "(coverage vs accuracy) sobre las predicciones OOD de la Fase 2, sin "
            "reentrenar nada."
        )
    )
    parser.add_argument("--oof", type=Path, default=OOF_POR_DEFECTO)
    parser.add_argument("--salida-json", type=Path, default=SALIDA_JSON_POR_DEFECTO)
    parser.add_argument("--salida-reliability", type=Path, default=SALIDA_RELIABILITY_POR_DEFECTO)
    parser.add_argument("--salida-coverage", type=Path, default=SALIDA_COVERAGE_POR_DEFECTO)
    parser.add_argument("--n-bins", type=int, default=N_BINS)
    args = parser.parse_args()

    if not args.oof.exists():
        print(f"No existe el archivo de predicciones OOF: {args.oof}", file=sys.stderr)
        sys.exit(1)

    oof = cargar_oof(args.oof)
    print(f"{len(oof):,} predicciones OOD cargadas desde {args.oof}")
    print(f"Accuracy global OOD: {oof['si_correcta'].mean():.4f}")

    print(f"\n=== Coverage vs accuracy (umbrales {UMBRALES}) ===")
    resultados_umbral = coverage_vs_accuracy(oof, UMBRALES)
    for r in resultados_umbral:
        acc = r["accuracy_aceptadas"]
        acc_txt = f"{acc:.4f}" if acc is not None else "n/a"
        print(
            f"  umbral={r['umbral']:.1f}  coverage={r['coverage']:.4f}  "
            f"filas={r['filas_aceptadas']:,}  accuracy_aceptadas={acc_txt}"
        )

    print(f"\n=== Curva de calibracion ({args.n_bins} bins) ===")
    bins = curva_calibracion(oof, args.n_bins)
    for b in bins:
        if b["soporte"] == 0:
            print(f"  bin {b['bin']} {b['rango']}: sin datos")
            continue
        print(
            f"  bin {b['bin']} {b['rango']}: soporte={b['soporte']:,} "
            f"confianza_media={b['confianza_media']:.4f} "
            f"accuracy_observada={b['accuracy_observada']:.4f}"
        )

    ece = expected_calibration_error(bins, len(oof))
    brier = brier_score_multiclase(oof)
    print(f"\nExpected Calibration Error (ECE): {ece:.4f}")
    print(f"Brier score multiclase: {brier:.4f}")

    args.salida_reliability.parent.mkdir(parents=True, exist_ok=True)
    graficar_reliability(bins, ece, args.salida_reliability)
    print(f"\nGrafica de calibracion guardada en {args.salida_reliability}")

    args.salida_coverage.parent.mkdir(parents=True, exist_ok=True)
    graficar_coverage_accuracy(resultados_umbral, args.salida_coverage)
    print(f"Grafica de coverage vs accuracy guardada en {args.salida_coverage}")

    salida = {
        "oof_predicciones_csv": str(args.oof),
        "filas_oof": int(len(oof)),
        "accuracy_global_ood": float(oof["si_correcta"].mean()),
        "categorias": list(CATEGORIAS),
        "coverage_vs_accuracy": resultados_umbral,
        "curva_calibracion": {
            "n_bins": args.n_bins,
            "bins": bins,
        },
        "expected_calibration_error": ece,
        "brier_score_multiclase": brier,
        "graficas": {
            "reliability": str(args.salida_reliability),
            "coverage_accuracy": str(args.salida_coverage),
        },
    }

    args.salida_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.salida_json, "w", encoding="utf-8") as fh:
        json.dump(salida, fh, ensure_ascii=False, indent=2)

    print(f"\nGuardado en {args.salida_json}")


if __name__ == "__main__":
    main()
