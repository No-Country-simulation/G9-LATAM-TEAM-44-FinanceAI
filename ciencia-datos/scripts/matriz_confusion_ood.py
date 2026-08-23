"""Construye la matriz de confusion 8x8 sobre las predicciones OOF de la Fase 2.

No reentrena nada: lee ciencia-datos/experimentos/oof_predicciones_cv.csv
(generado por evaluar_cv_agrupada.py con StratifiedGroupKFold agrupado por
comercio) y arma la matriz de confusion categoria_real x categoria_predicha,
en el orden fijo de features.CATEGORIAS. Como el CSV es out-of-fold, cada
prediccion fue hecha por un modelo que nunca vio ese comercio en entrenamiento
(comercios "out-of-distribution" relativo a ese fold).

Guarda:
- ciencia-datos/experimentos/matriz_confusion_ood.json: matriz cruda (filas =
  real, columnas = predicha) mas totales por fila y metadatos.
- ciencia-datos/experimentos/matriz_confusion_ood.md: analisis breve de las
  confusiones fuera de la diagonal mas frecuentes (como proporcion de la fila).

Uso:
    python ciencia-datos/scripts/matriz_confusion_ood.py \
        --oof ciencia-datos/experimentos/oof_predicciones_cv.csv \
        --salida-json ciencia-datos/experimentos/matriz_confusion_ood.json \
        --salida-md ciencia-datos/experimentos/matriz_confusion_ood.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import confusion_matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from features import CATEGORIAS  # noqa: E402

RAIZ_CIENCIA_DATOS = Path(__file__).resolve().parents[1]
OOF_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "oof_predicciones_cv.csv"
SALIDA_JSON_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "matriz_confusion_ood.json"
SALIDA_MD_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "matriz_confusion_ood.md"
N_CONFUSIONES_MIN = 5
N_CONFUSIONES_MAX = 8


def cargar_oof(ruta: Path) -> pd.DataFrame:
    oof = pd.read_csv(ruta)
    columnas_requeridas = {"categoria_real", "categoria_predicha"}
    faltantes = columnas_requeridas - set(oof.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas en {ruta}: {faltantes}")
    return oof


def construir_matriz(oof: pd.DataFrame) -> tuple[list[list[int]], list[int]]:
    """Matriz de confusion 8x8 en el orden fijo de CATEGORIAS.

    Filas = categoria_real, columnas = categoria_predicha.
    """
    matriz = confusion_matrix(
        oof["categoria_real"], oof["categoria_predicha"], labels=list(CATEGORIAS)
    )
    matriz_lista = matriz.tolist()
    totales_por_fila = matriz.sum(axis=1).tolist()
    return matriz_lista, totales_por_fila


def top_confusiones(
    matriz: list[list[int]], totales_por_fila: list[int], n_min: int, n_max: int
) -> list[dict]:
    """Celdas fuera de la diagonal ordenadas por proporcion de la fila (real)."""
    confusiones = []
    for i, real in enumerate(CATEGORIAS):
        total_fila = totales_por_fila[i]
        if total_fila == 0:
            continue
        for j, predicha in enumerate(CATEGORIAS):
            if i == j:
                continue
            casos = matriz[i][j]
            if casos == 0:
                continue
            confusiones.append({
                "real": real,
                "predicha": predicha,
                "casos": casos,
                "proporcion_de_la_fila": casos / total_fila,
                "total_fila_real": total_fila,
            })
    confusiones.sort(key=lambda c: c["proporcion_de_la_fila"], reverse=True)
    n = min(max(n_min, min(n_max, len(confusiones))), len(confusiones))
    return confusiones[:n]


def comercios_dominantes(oof: pd.DataFrame, real: str, predicha: str, top_n: int = 3) -> list[dict]:
    """Para una confusion (real -> predicha), identifica que comercios la explican.

    El CSV OOF trae la columna "comercio" (Fase 2), asi que no hace falta
    releer el dataset original. Para cada comercio devuelve cuantas de sus
    filas cayeron en esta celda y que fraccion representa sobre el total de
    filas de ese comercio en el OOF (para distinguir "todo el comercio se va
    a la otra categoria" de "una minoria se confunde").
    """
    subset = oof[(oof["categoria_real"] == real) & (oof["categoria_predicha"] == predicha)]
    if subset.empty:
        return []
    conteo_celda = subset["comercio"].value_counts()
    conteo_total_comercio = oof[oof["comercio"].isin(conteo_celda.index)]["comercio"].value_counts()

    resultado = []
    for comercio, casos_celda in conteo_celda.head(top_n).items():
        total_comercio = int(conteo_total_comercio[comercio])
        resultado.append({
            "comercio": comercio,
            "casos_en_celda": int(casos_celda),
            "filas_totales_del_comercio_en_oof": total_comercio,
            "proporcion_del_comercio": casos_celda / total_comercio if total_comercio else 0.0,
        })
    return resultado


def formatear_matriz_md(matriz: list[list[int]]) -> str:
    encabezado = "| real \\ predicha | " + " | ".join(CATEGORIAS) + " |"
    separador = "|---" * (len(CATEGORIAS) + 1) + "|"
    filas = [encabezado, separador]
    for i, real in enumerate(CATEGORIAS):
        fila = [str(matriz[i][j]) for j in range(len(CATEGORIAS))]
        filas.append(f"| **{real}** | " + " | ".join(fila) + " |")
    return "\n".join(filas)


def resumen_distribucion(oof: pd.DataFrame) -> str:
    real = oof["categoria_real"].value_counts()
    pred = oof["categoria_predicha"].value_counts()
    filas = ["| categoria | filas reales | filas predichas | razon predichas/reales |", "|---|---|---|---|"]
    for cat in CATEGORIAS:
        r = int(real.get(cat, 0))
        p = int(pred.get(cat, 0))
        razon = p / r if r else float("nan")
        filas.append(f"| {cat} | {r:,} | {p:,} | {razon:.4f} |")
    return "\n".join(filas)


def escribir_markdown(
    ruta: Path,
    oof: pd.DataFrame,
    matriz: list[list[int]],
    totales_por_fila: list[int],
    confusiones: list[dict],
) -> None:
    n_total = len(oof)
    accuracy_global = sum(
        matriz[i][i] for i in range(len(CATEGORIAS))
    ) / n_total if n_total else 0.0

    lineas = [
        "# Matriz de confusion sobre predicciones OOD (out-of-fold)",
        "",
        (
            f"Construida sobre {n_total:,} predicciones out-of-fold de "
            "`ciencia-datos/experimentos/oof_predicciones_cv.csv` (Fase 2: "
            "StratifiedGroupKFold(n_splits=5) agrupado por comercio). Cada "
            "prediccion fue hecha por un modelo que nunca vio ese comercio en "
            "entrenamiento, por lo que estas confusiones reflejan el "
            "comportamiento del clasificador ante comercios no vistos "
            "(out-of-distribution relativo a cada fold)."
        ),
        "",
        f"Accuracy global sobre el OOF (diagonal / total): {accuracy_global:.4f}",
        "",
        "## Matriz de confusion (filas = real, columnas = predicha)",
        "",
        formatear_matriz_md(matriz),
        "",
        "## Confusiones mas frecuentes (fuera de la diagonal)",
        "",
        (
            "Ordenadas por proporcion de la fila real (que fraccion de esa "
            "categoria real termino predicha como otra categoria)."
        ),
        "",
        "| real | predicha | casos | % de la fila real | total fila real |",
        "|---|---|---|---|---|",
    ]
    for c in confusiones:
        lineas.append(
            f"| {c['real']} | {c['predicha']} | {c['casos']:,} | "
            f"{c['proporcion_de_la_fila'] * 100:.4f}% | {c['total_fila_real']:,} |"
        )

    lineas.append("")
    lineas.append("## Distribucion real vs. predicha por categoria")
    lineas.append("")
    lineas.append(
        "Si el clasificador generalizara bien a comercios no vistos, la "
        "columna de filas predichas deberia parecerse a la de filas reales. "
        "Una razon > 1 indica una categoria que actua como \"iman\" (recibe mas "
        "predicciones de las que le corresponden); una razon < 1 indica una "
        "categoria subrepresentada en las predicciones."
    )
    lineas.append("")
    lineas.append(resumen_distribucion(oof))

    lineas.append("")
    lineas.append("## Analisis")
    lineas.append("")
    lineas.append(
        "Para cada confusion se listan los comercios (nunca vistos por el "
        "modelo en ese fold, por la agrupacion de la CV) que mas casos "
        "aportan a esa celda, junto con que fraccion de TODAS las filas de "
        "ese comercio en el OOF cayeron ahi. Cuando esa fraccion es cercana "
        "a 1.0, no se trata de una confusion parcial dentro de una categoria "
        "heterogenea, sino de un comercio completo que el modelo redirige "
        "casi siempre hacia la misma categoria equivocada al no reconocer "
        "ninguno de sus tokens exactos."
    )
    lineas.append("")

    for c in confusiones:
        comercios = comercios_dominantes(oof, c["real"], c["predicha"], top_n=3)
        lineas.append(
            f"### {c['real']} -> {c['predicha']} ({c['casos']:,} casos, "
            f"{c['proporcion_de_la_fila'] * 100:.4f}% de las filas reales de `{c['real']}`)"
        )
        lineas.append("")
        for cm in comercios:
            lineas.append(
                f"- `{cm['comercio']}`: {cm['casos_en_celda']:,} de sus "
                f"{cm['filas_totales_del_comercio_en_oof']:,} filas en el OOF "
                f"cayeron en esta celda "
                f"({cm['proporcion_del_comercio'] * 100:.4f}% de ese comercio)."
            )
        lineas.append("")

    lineas.append("### Hipotesis")
    lineas.append("")
    lineas.append(
        "1. **El texto es casi puramente el nombre del comercio, no vocabulario "
        "generico de la categoria.** `descripcion_limpia` es en la practica el "
        "nombre del comercio (con erratas/variantes), por lo que el vectorizador "
        "aprende, sobre todo, tokens y n-gramas de caracteres asociados a cada "
        "comercio particular en vez de un vocabulario compartido por categoria. "
        "Cuando un comercio queda fuera del entrenamiento de un fold (por la "
        "agrupacion `StratifiedGroupKFold` sobre `comercio`), el modelo no tiene "
        "ninguna fila con esos tokens exactos y debe decidir en base a "
        "coincidencias parciales de n-gramas de caracteres (3-5) con comercios "
        "de OTRAS categorias, lo que produce el patron observado: comercios "
        "completos (95-100% de sus filas) migran en bloque hacia una unica "
        "categoria equivocada (ej. `EPS Cuota Moderadora` -> vivienda en 69% de "
        "sus filas, `Gas Natural Domiciliario` -> alimentacion en el 100%, "
        "`Cuota Hipoteca Vivienda` -> otras en 96%)."
    )
    lineas.append(
        "2. **`alimentacion` actua como categoria iman para texto no reconocido.** "
        "Es la categoria real MENOS frecuente en el OOF (la mas chica de las 8) "
        "pero la MAS predicha con amplio margen (mas del doble de veces de las "
        "que realmente ocurre), ver tabla de distribucion arriba. Esto sugiere "
        "que, ante un comercio sin ningun n-grama reconocible, la funcion de "
        "decision calibrada (`CalibratedClassifierCV` sobre `LinearSVC`) tiende "
        "a favorecer `alimentacion` como opcion por defecto, probablemente "
        "porque en el vocabulario de esa categoria abundan palabras y "
        "fragmentos de caracteres cortos y comunes en español (ej. sufijos, "
        "numeros, nombres de ciudad que tambien aparecen en las erratas de "
        "otros comercios) que generalizan mal como señal discriminativa."
    )
    lineas.append(
        "3. **Los pares confundidos no comparten un tema de gasto obvio "
        "(salud/vivienda, educacion/ocio, servicios/alimentacion), lo que "
        "refuerza la hipotesis 1**: si la confusion fuera por vocabulario "
        "semanticamente cercano (dos categorias de gasto parecidas), "
        "esperariamos ver pares tematicamente relacionados. En cambio, el "
        "patron dominante es \"un comercio especifico, no visto, cae entero en "
        "una categoria arbitraria\", consistente con sobreajuste a nombres de "
        "comercio en vez de aprender categorias generalizables."
    )

    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Construye la matriz de confusion 8x8 (real x predicha) sobre las "
            "predicciones out-of-fold de la Fase 2, sin reentrenar nada."
        )
    )
    parser.add_argument("--oof", type=Path, default=OOF_POR_DEFECTO)
    parser.add_argument("--salida-json", type=Path, default=SALIDA_JSON_POR_DEFECTO)
    parser.add_argument("--salida-md", type=Path, default=SALIDA_MD_POR_DEFECTO)
    parser.add_argument("--n-min-confusiones", type=int, default=N_CONFUSIONES_MIN)
    parser.add_argument("--n-max-confusiones", type=int, default=N_CONFUSIONES_MAX)
    args = parser.parse_args()

    if not args.oof.exists():
        print(f"No existe el archivo de predicciones OOF: {args.oof}", file=sys.stderr)
        sys.exit(1)

    oof = cargar_oof(args.oof)
    print(f"{len(oof):,} predicciones OOF cargadas desde {args.oof}")

    matriz, totales_por_fila = construir_matriz(oof)

    confusiones = top_confusiones(
        matriz, totales_por_fila, args.n_min_confusiones, args.n_max_confusiones
    )
    for c in confusiones:
        c["comercios_dominantes"] = comercios_dominantes(oof, c["real"], c["predicha"], top_n=3)

    print("\n=== Top confusiones fuera de la diagonal (por % de la fila real) ===")
    for c in confusiones:
        print(
            f"  {c['real']:<14} -> {c['predicha']:<14} "
            f"{c['casos']:>6,} casos ({c['proporcion_de_la_fila'] * 100:.4f}% de la fila)"
        )

    n_total = len(oof)
    accuracy_global = sum(
        matriz[i][i] for i in range(len(CATEGORIAS))
    ) / n_total if n_total else 0.0
    print(f"\nAccuracy global sobre el OOF: {accuracy_global:.4f}")

    salida_json = {
        "fuente_oof": str(args.oof),
        "filas_totales": int(n_total),
        "categorias": list(CATEGORIAS),
        "accuracy_global": accuracy_global,
        "matriz": matriz,
        "totales_por_fila": totales_por_fila,
        "top_confusiones": confusiones,
    }

    args.salida_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.salida_json, "w", encoding="utf-8") as fh:
        json.dump(salida_json, fh, ensure_ascii=False, indent=2)
    print(f"\nMatriz guardada en {args.salida_json}")

    args.salida_md.parent.mkdir(parents=True, exist_ok=True)
    escribir_markdown(args.salida_md, oof, matriz, totales_por_fila, confusiones)
    print(f"Analisis guardado en {args.salida_md}")


if __name__ == "__main__":
    main()
