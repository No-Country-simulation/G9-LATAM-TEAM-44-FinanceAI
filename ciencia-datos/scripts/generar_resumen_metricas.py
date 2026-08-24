"""Condensa los artefactos de ciencia-datos/experimentos/ en un JSON pequeno
para que srv-python (y, en espejo, srv-java) lo expongan al frontend.

No reentrena ni recalcula nada: agrega en un solo archivo los resultados que
ya dejaron las Fases 1-5 y 9-11 del roadmap DS (baseline, CV agrupada por
comercio, matriz de confusion OOD, metricas por categoria, calibracion y
benchmark contra modelos clasicos). En particular, NO reproduce las 58,894
filas de `oof_predicciones_cv.csv`; solo sus agregados ya calculados en los
otros artefactos.

Lee:
  - ciencia-datos/experimentos/baseline_v1.json           (Fase 1)
  - ciencia-datos/experimentos/cv_agrupada_comercio.json  (Fase 2)
  - ciencia-datos/experimentos/matriz_confusion_ood.json  (Fase 3)
  - ciencia-datos/experimentos/metricas_por_categoria.csv (Fase 4)
  - ciencia-datos/experimentos/calibracion.json           (Fase 5)
  - ciencia-datos/experimentos/benchmark_clasico.csv      (Fases 9-11)
  - ciencia-datos/artefactos/metadatos.json               (version y fecha)

Escribe:
  - ciencia-datos/artefactos/metricas_resumen.json

Uso:
    python ciencia-datos/scripts/generar_resumen_metricas.py \
        --experimentos ciencia-datos/experimentos \
        --artefactos ciencia-datos/artefactos \
        --salida ciencia-datos/artefactos/metricas_resumen.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from features import CATEGORIAS  # noqa: E402

RAIZ_CIENCIA_DATOS = Path(__file__).resolve().parents[1]
EXPERIMENTOS_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos"
ARTEFACTOS_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "artefactos"
SALIDA_POR_DEFECTO = ARTEFACTOS_POR_DEFECTO / "metricas_resumen.json"

#: Filas del CSV de metricas por categoria que son agregados, no una de las 8
#: categorias (Fase 4, metricas_por_categoria.py).
FILAS_AGREGADO = {"macro", "weighted"}


def _leer_json(ruta: Path) -> dict:
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el artefacto: {ruta}")
    with open(ruta, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _leer_csv(ruta: Path) -> list[dict]:
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el artefacto: {ruta}")
    with open(ruta, "r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def resumen_baseline(baseline: dict) -> dict:
    """Accuracy/f1 de la particion aleatoria vs. la particion por comercio no
    visto (Fase 1): la brecha entre ambas es la evidencia central de que el
    modelo memoriza comercios en vez de generalizar."""
    aleatoria = baseline["particion_aleatoria"]["metricas"]
    por_comercio = baseline["particion_por_comercio"]["metricas"]
    return {
        "particion_aleatoria": {
            "accuracy": aleatoria["accuracy"],
            "f1_macro": aleatoria["f1_macro"],
        },
        "comercio_no_visto": {
            "accuracy": por_comercio["accuracy"],
            "f1_macro": por_comercio["f1_macro"],
        },
    }


def resumen_cv_agrupada(cv: dict) -> dict:
    """Media y desviacion estandar de las 4 metricas sobre los 5 folds
    agrupados por comercio (Fase 2)."""
    return cv["resumen_metricas"]


def resumen_matriz_confusion(matriz: dict) -> dict:
    """Matriz 8x8 (real x predicha) en el orden fijo de features.CATEGORIAS
    (Fase 3), mas la accuracy global sobre el OOF que la genero."""
    categorias = list(matriz["categorias"])
    if categorias != list(CATEGORIAS):
        raise ValueError(
            "El orden de categorias de matriz_confusion_ood.json no coincide "
            "con features.CATEGORIAS; regenera el artefacto o revisa features.py."
        )
    return {
        "categorias": categorias,
        "matriz": matriz["matriz"],
        "accuracy_global": matriz["accuracy_global"],
    }


def resumen_metricas_por_categoria(filas: list[dict]) -> list[dict]:
    """Precision/recall/f1/soporte por categoria (Fase 4), sin las filas de
    agregado macro/weighted: quedan 8, una por categoria."""
    resultado = []
    for fila in filas:
        if fila["categoria"] in FILAS_AGREGADO:
            continue
        resultado.append({
            "categoria": fila["categoria"],
            "precision": float(fila["precision"]),
            "recall": float(fila["recall"]),
            "f1_score": float(fila["f1_score"]),
            "soporte": int(fila["soporte"]),
            "tasa_error": float(fila["tasa_error"]),
        })
    return resultado


def resumen_calibracion(calibracion: dict) -> dict:
    """Tabla coverage_vs_accuracy (la base de la estrategia de abstencion de
    la Fase 12) mas las metricas globales de calibracion (Fase 5)."""
    return {
        "coverage_vs_accuracy": calibracion["coverage_vs_accuracy"],
        "expected_calibration_error": calibracion["expected_calibration_error"],
        "brier_score_multiclase": calibracion["brier_score_multiclase"],
    }


def resumen_benchmark(filas: list[dict]) -> list[dict]:
    """Filas del benchmark contra modelos clasicos y variantes de features
    (Fases 9-11), tal cual estan en el CSV."""
    return filas


def construir_resumen(experimentos: Path, artefactos: Path) -> dict:
    baseline = _leer_json(experimentos / "baseline_v1.json")
    cv_agrupada = _leer_json(experimentos / "cv_agrupada_comercio.json")
    matriz = _leer_json(experimentos / "matriz_confusion_ood.json")
    calibracion = _leer_json(experimentos / "calibracion.json")
    metricas_por_categoria = _leer_csv(experimentos / "metricas_por_categoria.csv")
    benchmark = _leer_csv(experimentos / "benchmark_clasico.csv")
    metadatos = _leer_json(artefactos / "metadatos.json")

    return {
        "version_modelo": metadatos.get("version"),
        "fecha": metadatos.get("entrenado_en"),
        "baseline": resumen_baseline(baseline),
        "cv_agrupada": resumen_cv_agrupada(cv_agrupada),
        "matriz_confusion": resumen_matriz_confusion(matriz),
        "metricas_por_categoria": resumen_metricas_por_categoria(metricas_por_categoria),
        "calibracion": resumen_calibracion(calibracion),
        "benchmark": resumen_benchmark(benchmark),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Condensa los artefactos de ciencia-datos/experimentos/ en un solo "
            "JSON pequeno para que srv-python (y srv-java, en espejo) lo "
            "expongan al frontend sin cargar el CSV OOF completo."
        )
    )
    parser.add_argument("--experimentos", type=Path, default=EXPERIMENTOS_POR_DEFECTO)
    parser.add_argument("--artefactos", type=Path, default=ARTEFACTOS_POR_DEFECTO)
    parser.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO)
    args = parser.parse_args()

    resumen = construir_resumen(args.experimentos, args.artefactos)

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with open(args.salida, "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=2)

    print(f"Resumen guardado en {args.salida}")
    print(f"  version_modelo={resumen['version_modelo']} fecha={resumen['fecha']}")
    print(f"  categorias en metricas_por_categoria: {len(resumen['metricas_por_categoria'])}")
    print(f"  filas en benchmark: {len(resumen['benchmark'])}")
    print(f"  ECE={resumen['calibracion']['expected_calibration_error']:.4f} "
          f"Brier={resumen['calibracion']['brier_score_multiclase']:.4f}")


if __name__ == "__main__":
    main()
