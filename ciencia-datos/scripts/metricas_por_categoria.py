"""Metricas de clasificacion por categoria sobre las predicciones OOF de la Fase 2.

No reentrena nada: lee ciencia-datos/experimentos/oof_predicciones_cv.csv
(generado por evaluar_cv_agrupada.py con StratifiedGroupKFold agrupado por
comercio) y calcula, para cada una de las 8 categorias de features.CATEGORIAS,
precision, recall, f1-score, soporte (filas reales de esa categoria en el OOF)
y tasa de error (1 - recall).

Guarda:
- ciencia-datos/experimentos/metricas_por_categoria.csv: una fila por
  categoria (en el orden fijo de CATEGORIAS) mas dos filas de resumen
  ("macro" y "weighted").
- ciencia-datos/experimentos/metricas_por_categoria.md: la misma tabla en
  formato legible mas un comentario breve señalando la categoria mas fuerte,
  la mas debil y la de menor soporte.

Uso:
    python ciencia-datos/scripts/metricas_por_categoria.py \
        --oof ciencia-datos/experimentos/oof_predicciones_cv.csv \
        --salida-csv ciencia-datos/experimentos/metricas_por_categoria.csv \
        --salida-md ciencia-datos/experimentos/metricas_por_categoria.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import precision_recall_fscore_support

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from features import CATEGORIAS  # noqa: E402

RAIZ_CIENCIA_DATOS = Path(__file__).resolve().parents[1]
OOF_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "oof_predicciones_cv.csv"
SALIDA_CSV_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "metricas_por_categoria.csv"
SALIDA_MD_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "metricas_por_categoria.md"


def cargar_oof(ruta: Path) -> pd.DataFrame:
    oof = pd.read_csv(ruta)
    columnas_requeridas = {"categoria_real", "categoria_predicha"}
    faltantes = columnas_requeridas - set(oof.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas en {ruta}: {faltantes}")
    return oof


def calcular_metricas_por_categoria(oof: pd.DataFrame) -> pd.DataFrame:
    """Precision/recall/f1/soporte por categoria, en el orden fijo de CATEGORIAS."""
    y_real = oof["categoria_real"]
    y_pred = oof["categoria_predicha"]

    precision, recall, f1, soporte = precision_recall_fscore_support(
        y_real, y_pred, labels=list(CATEGORIAS), zero_division=0
    )

    filas = []
    for i, categoria in enumerate(CATEGORIAS):
        filas.append({
            "categoria": categoria,
            "precision": precision[i],
            "recall": recall[i],
            "f1_score": f1[i],
            "soporte": int(soporte[i]),
            "tasa_error": 1.0 - recall[i],
        })
    tabla = pd.DataFrame(filas)

    # --- filas de resumen: macro (promedio simple) y weighted (por soporte) ---
    precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
        y_real, y_pred, labels=list(CATEGORIAS), average="macro", zero_division=0
    )
    precision_ponderada, recall_ponderada, f1_ponderada, _ = precision_recall_fscore_support(
        y_real, y_pred, labels=list(CATEGORIAS), average="weighted", zero_division=0
    )
    soporte_total = int(tabla["soporte"].sum())

    resumen = pd.DataFrame([
        {
            "categoria": "macro",
            "precision": precision_macro,
            "recall": recall_macro,
            "f1_score": f1_macro,
            "soporte": soporte_total,
            "tasa_error": 1.0 - recall_macro,
        },
        {
            "categoria": "weighted",
            "precision": precision_ponderada,
            "recall": recall_ponderada,
            "f1_score": f1_ponderada,
            "soporte": soporte_total,
            "tasa_error": 1.0 - recall_ponderada,
        },
    ])

    return pd.concat([tabla, resumen], ignore_index=True)


def formatear_tabla_md(tabla: pd.DataFrame) -> str:
    encabezado = "| categoria | precision | recall | f1-score | soporte | tasa de error |"
    separador = "|---|---|---|---|---|---|"
    filas = [encabezado, separador]
    for _, fila in tabla.iterrows():
        etiqueta = f"**{fila['categoria']}**" if fila["categoria"] in ("macro", "weighted") else fila["categoria"]
        filas.append(
            f"| {etiqueta} | {fila['precision']:.4f} | {fila['recall']:.4f} | "
            f"{fila['f1_score']:.4f} | {fila['soporte']:,} | {fila['tasa_error']:.4f} |"
        )
    return "\n".join(filas)


def escribir_markdown(ruta: Path, tabla: pd.DataFrame, oof: pd.DataFrame) -> None:
    solo_categorias = tabla[~tabla["categoria"].isin(("macro", "weighted"))].reset_index(drop=True)

    mas_fuerte = solo_categorias.loc[solo_categorias["f1_score"].idxmax()]
    mas_debil = solo_categorias.loc[solo_categorias["f1_score"].idxmin()]
    menos_soporte = solo_categorias.loc[solo_categorias["soporte"].idxmin()]

    lineas = [
        "# Metricas por categoria sobre predicciones OOF (out-of-fold)",
        "",
        (
            f"Calculadas sobre {len(oof):,} predicciones out-of-fold de "
            "`ciencia-datos/experimentos/oof_predicciones_cv.csv` (Fase 2: "
            "StratifiedGroupKFold(n_splits=5) agrupado por comercio), sin "
            "reentrenar nada. `soporte` es el numero de filas reales de esa "
            "categoria en el OOF; `tasa_error` es `1 - recall` (proporcion de "
            "esa categoria real mal clasificada)."
        ),
        "",
        "## Metricas",
        "",
        formatear_tabla_md(tabla),
        "",
        "## Analisis",
        "",
        (
            f"- **Categoria mas fuerte:** `{mas_fuerte['categoria']}` "
            f"(f1-score {mas_fuerte['f1_score']:.4f}, precision "
            f"{mas_fuerte['precision']:.4f}, recall {mas_fuerte['recall']:.4f}, "
            f"soporte {int(mas_fuerte['soporte']):,}); es la categoria que el "
            "clasificador reconoce con mayor consistencia en comercios no vistos."
        ),
        (
            f"- **Categoria mas debil:** `{mas_debil['categoria']}` "
            f"(f1-score {mas_debil['f1_score']:.4f}, precision "
            f"{mas_debil['precision']:.4f}, recall {mas_debil['recall']:.4f}, "
            f"tasa de error {mas_debil['tasa_error']:.4f}); es donde el modelo "
            "confunde con mayor frecuencia comercios no vistos en entrenamiento."
        ),
        (
            f"- **Menor soporte:** `{menos_soporte['categoria']}` "
            f"({int(menos_soporte['soporte']):,} filas reales en el OOF, "
            f"f1-score {menos_soporte['f1_score']:.4f}); al ser la categoria con "
            "menos ejemplos, es la candidata mas clara a necesitar mas datos "
            "etiquetados antes de sacar conclusiones fuertes sobre su desempeño."
        ),
        "",
    ]

    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Calcula precision/recall/f1/soporte/tasa de error por categoria "
            "sobre las predicciones out-of-fold de la Fase 2, sin reentrenar nada."
        )
    )
    parser.add_argument("--oof", type=Path, default=OOF_POR_DEFECTO)
    parser.add_argument("--salida-csv", type=Path, default=SALIDA_CSV_POR_DEFECTO)
    parser.add_argument("--salida-md", type=Path, default=SALIDA_MD_POR_DEFECTO)
    args = parser.parse_args()

    if not args.oof.exists():
        print(f"No existe el archivo de predicciones OOF: {args.oof}", file=sys.stderr)
        sys.exit(1)

    oof = cargar_oof(args.oof)
    print(f"{len(oof):,} predicciones OOF cargadas desde {args.oof}")

    tabla = calcular_metricas_por_categoria(oof)

    print("\n=== Metricas por categoria ===")
    for _, fila in tabla.iterrows():
        print(
            f"  {fila['categoria']:<10} precision={fila['precision']:.4f} "
            f"recall={fila['recall']:.4f} f1={fila['f1_score']:.4f} "
            f"soporte={int(fila['soporte']):,} tasa_error={fila['tasa_error']:.4f}"
        )

    args.salida_csv.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(args.salida_csv, index=False)
    print(f"\nMetricas guardadas en {args.salida_csv}")

    args.salida_md.parent.mkdir(parents=True, exist_ok=True)
    escribir_markdown(args.salida_md, tabla, oof)
    print(f"Analisis guardado en {args.salida_md}")


if __name__ == "__main__":
    main()
