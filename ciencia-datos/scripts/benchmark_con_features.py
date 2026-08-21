"""Benchmark "solo texto" vs. "texto + features adicionales" (Fase 10).

Parte del ganador de la Fase 9 (ciencia-datos/experimentos/benchmark_clasico.csv):
el benchmark de modelos clasicos no mostro una mejora clara sobre el pipeline
vigente (palabra+caracter TFIDF + LinearSVC calibrado; los candidatos quedaron
dentro de una desviacion estandar del actual), asi que esta fase usa ESE mismo
pipeline como base y le agrega, uno por uno y luego todos juntos, bloques de
features adicionales sin fuga de la categoria real:

- monto y log1p(monto) (se prueban por separado para decidir cual ayuda mas).
- longitud_texto = len(descripcion_limpia).
- flags binarios de presencia, en la columna "descripcion" ORIGINAL (no la
  limpia, porque normalizar_texto() le quita estos tokens a proposito), de:
  pos, trf, compra, pago, debito, credito, tarj.
- dia_de_semana y mes de la columna "fecha" (estacionalidad, ej. servicios a
  fin de mes), codificados con OneHotEncoder.

Mismo split que siempre: StratifiedGroupKFold(n_splits=5, shuffle=True,
random_state=42) agrupando por "comercio" (igual que la Fase 2 y la Fase 9).

Uso:
    python ciencia-datos/scripts/benchmark_con_features.py \
        --datos ciencia-datos/datos/limpios/transacciones.csv \
        --salida ciencia-datos/experimentos/benchmark_clasico.csv
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import LinearSVC

RAIZ_CIENCIA_DATOS = Path(__file__).resolve().parents[1]
DATOS_POR_DEFECTO = (
    "C:/Users/HardM/Desktop/Enterprise/hackaton-alura/G9-LATAM-TEAM-44-FinanceAI/"
    "ciencia-datos/datos/limpios/transacciones.csv"
)
SALIDA_CSV_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "benchmark_clasico.csv"
SALIDA_MD_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "benchmark_con_features.md"
N_SPLITS = 5
SEMILLA = 42

#: Tokens de ruido de extracto bancario que normalizar_texto() quita a
#: proposito de "descripcion_limpia". Se buscan en la columna "descripcion"
#: ORIGINAL (sin limpiar) para no perder la senal.
TOKENS_PREFIJO = ("pos", "trf", "compra", "pago", "debito", "credito", "tarj")


# ------------------------------------------------------------- vectorizadores

def vectorizador_completo() -> FeatureUnion:
    """Igual que la Fase 9 / notebook seccion 9. No modificar."""
    return FeatureUnion([
        ("palabra", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
        ("caracter", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3, sublinear_tf=True)),
    ])


# ---------------------------------------------------------- ingenieria de features

def quitar_tildes_ascii(texto: str) -> str:
    import unicodedata
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def construir_features_adicionales(entrenables: pd.DataFrame) -> pd.DataFrame:
    """Agrega columnas derivadas SIN usar la categoria real (sin fuga).

    - monto, log_monto: de la columna "monto" tal cual (siempre > 0 en este
      dataset para egresos).
    - longitud_texto: len(descripcion_limpia).
    - flag_<token>: presencia de cada token de TOKENS_PREFIJO en la columna
      "descripcion" ORIGINAL (sin tildes, insensible a mayusculas), como
      palabra completa.
    - dia_semana, mes: de "fecha" (0-6 y 1-12).
    """
    df = entrenables.copy()

    df["monto"] = df["monto"].astype(float)
    df["log_monto"] = np.log1p(df["monto"])
    df["longitud_texto"] = df["descripcion_limpia"].fillna("").str.len().astype(float)

    descripcion_original_norm = (
        df["descripcion"].fillna("").map(quitar_tildes_ascii).str.lower()
    )
    for token in TOKENS_PREFIJO:
        patron = re.compile(rf"\b{token}\b")
        df[f"flag_{token}"] = descripcion_original_norm.map(
            lambda s, p=patron: 1.0 if p.search(s) else 0.0
        )

    fecha = pd.to_datetime(df["fecha"], errors="coerce")
    df["dia_semana"] = fecha.dt.dayofweek.fillna(-1).astype(int)
    df["mes"] = fecha.dt.month.fillna(-1).astype(int)

    return df


COLUMNAS_FLAGS = tuple(f"flag_{t}" for t in TOKENS_PREFIJO)


def construir_column_transformer(
    usar_monto: bool = False,
    usar_log_monto: bool = False,
    usar_longitud: bool = False,
    usar_flags: bool = False,
    usar_temporal: bool = False,
) -> ColumnTransformer:
    """Texto (TF-IDF palabra+caracter) siempre; el resto es opcional.

    Las numericas (monto/log_monto/longitud/flags) se escalan con
    StandardScaler; dia_semana/mes van con OneHotEncoder porque son
    categoricas ciclicas, no ordinales.
    """
    transformadores: list[tuple] = [
        ("texto", vectorizador_completo(), "descripcion_limpia"),
    ]

    columnas_numericas: list[str] = []
    if usar_monto:
        columnas_numericas.append("monto")
    if usar_log_monto:
        columnas_numericas.append("log_monto")
    if usar_longitud:
        columnas_numericas.append("longitud_texto")
    if usar_flags:
        columnas_numericas.extend(COLUMNAS_FLAGS)
    if columnas_numericas:
        transformadores.append(("numerico", StandardScaler(), columnas_numericas))

    if usar_temporal:
        transformadores.append((
            "temporal",
            OneHotEncoder(handle_unknown="ignore"),
            ["dia_semana", "mes"],
        ))

    return ColumnTransformer(transformadores)


def pipeline_svc_calibrado(semilla: int, column_transformer_kwargs: dict) -> Callable[[int], Pipeline]:
    def construir(semilla_interna: int) -> Pipeline:
        return Pipeline([
            ("features", construir_column_transformer(**column_transformer_kwargs)),
            ("clf", CalibratedClassifierCV(LinearSVC(C=1.0, random_state=semilla_interna), cv=3)),
        ])
    return construir


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
    X: pd.DataFrame,
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


def solapan(r1: dict, r2: dict, metrica: str = "f1_macro") -> bool:
    """True si media +/- std de r1 y r2 se solapan en la metrica dada."""
    m1, s1 = r1["resumen"][metrica]
    m2, s2 = r2["resumen"][metrica]
    return (m1 - s1) <= (m2 + s2) and (m2 - s2) <= (m1 + s1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark 'solo texto' vs. 'texto + features adicionales' sobre el "
            "mismo split StratifiedGroupKFold agrupado por comercio de siempre."
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
    entrenables = construir_features_adicionales(entrenables)
    print(
        f"{len(entrenables):,} egresos etiquetados | "
        f"{entrenables['comercio'].nunique()} comercios unicos"
    )
    for token in TOKENS_PREFIJO:
        print(f"  flag_{token}: {int(entrenables[f'flag_{token}'].sum()):,} filas en 1")

    columnas_features = [
        "descripcion_limpia", "monto", "log_monto", "longitud_texto",
        *COLUMNAS_FLAGS, "dia_semana", "mes",
    ]
    X = entrenables[columnas_features].reset_index(drop=True)
    y = entrenables["categoria"].reset_index(drop=True)
    comercio = entrenables["comercio"].reset_index(drop=True)

    candidatos: list[tuple[str, dict]] = [
        ("solo texto (control, igual pipeline vigente/Fase 9)", {}),
        ("+monto", dict(usar_monto=True)),
        ("+log1p(monto)", dict(usar_log_monto=True)),
        ("+longitud_texto", dict(usar_longitud=True)),
        ("+flags_prefijos_extracto", dict(usar_flags=True)),
        ("+dia_semana+mes", dict(usar_temporal=True)),
    ]

    resultados: list[dict] = []
    for nombre, kwargs in candidatos:
        resultados.append(
            evaluar_candidato(
                nombre,
                pipeline_svc_calibrado(args.semilla, kwargs),
                X, y, comercio, args.semilla,
            )
        )

    resultado_por_nombre = {nombre: r for (nombre, _), r in zip(candidatos, resultados)}
    resultado_monto = resultado_por_nombre["+monto"]
    resultado_log_monto = resultado_por_nombre["+log1p(monto)"]
    if resultado_log_monto["resumen"]["f1_macro"][0] >= resultado_monto["resumen"]["f1_macro"][0]:
        monto_elegido, kwargs_monto_elegido = "log1p(monto)", dict(usar_log_monto=True)
        monto_descartado = "monto"
    else:
        monto_elegido, kwargs_monto_elegido = "monto", dict(usar_monto=True)
        monto_descartado = "log1p(monto)"

    kwargs_todas = dict(usar_longitud=True, usar_flags=True, usar_temporal=True, **kwargs_monto_elegido)
    resultado_todas = evaluar_candidato(
        f"+todas las features (monto: {monto_elegido})",
        pipeline_svc_calibrado(args.semilla, kwargs_todas),
        X, y, comercio, args.semilla,
    )
    resultados.append(resultado_todas)
    candidatos.append((resultado_todas["modelo"], kwargs_todas))

    control = resultado_por_nombre["solo texto (control, igual pipeline vigente/Fase 9)"]

    # -------------------------------------------------------------------- CSV
    filas_nuevas = []
    for r in resultados:
        resumen = r["resumen"]
        filas_nuevas.append({
            "modelo": r["modelo"],
            "accuracy": formatear_media_std(resumen, "accuracy"),
            "f1_macro": formatear_media_std(resumen, "f1_macro"),
            "f1_weighted": formatear_media_std(resumen, "f1_weighted"),
            "balanced_accuracy": formatear_media_std(resumen, "balanced_accuracy"),
        })
    tabla_nueva = pd.DataFrame(filas_nuevas)

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    if args.salida.exists():
        tabla_previa = pd.read_csv(args.salida)
        # Evita duplicar filas si el script se corre mas de una vez: se
        # reemplazan las filas con el mismo nombre de modelo.
        tabla_previa = tabla_previa[~tabla_previa["modelo"].isin(tabla_nueva["modelo"])]
        tabla_final = pd.concat([tabla_previa, tabla_nueva], ignore_index=True)
    else:
        tabla_final = tabla_nueva
    tabla_final.to_csv(args.salida, index=False, encoding="utf-8")
    print(f"\nAmpliado CSV en {args.salida} (+{len(tabla_nueva)} filas 'Fase 10')")

    # --------------------------------------------------------------------- MD
    tabla_comparacion = tabla_nueva.copy()

    lineas_ablacion = []
    for nombre, _ in candidatos[1:-1]:  # excluye control y "+todas"
        r = resultado_por_nombre.get(nombre)
        if r is None:
            continue
        f1_r = r["resumen"]["f1_macro"]
        delta = f1_r[0] - control["resumen"]["f1_macro"][0]
        se_solapa = solapan(control, r)
        signo = "+" if delta >= 0 else ""
        veredicto = (
            "dentro de 1 desviacion estandar del control (no se distingue con confianza)"
            if se_solapa else
            ("mejora real" if delta > 0 else "empeora de forma real")
        )
        lineas_ablacion.append(
            f"- **{nombre}**: f1_macro = {formatear_media_std(r['resumen'], 'f1_macro')} "
            f"(delta vs. control = {signo}{delta:.4f}) -> {veredicto}."
        )

    delta_todas = resultado_todas["resumen"]["f1_macro"][0] - control["resumen"]["f1_macro"][0]
    se_solapa_todas = solapan(control, resultado_todas)
    signo_todas = "+" if delta_todas >= 0 else ""
    veredicto_todas = (
        "dentro de 1 desviacion estandar del control (no se distingue con confianza)"
        if se_solapa_todas else
        ("mejora real" if delta_todas > 0 else "empeora de forma real")
    )

    lineas_monto = (
        f"Entre **monto** (f1_macro = {formatear_media_std(resultado_monto['resumen'], 'f1_macro')}) "
        f"y **log1p(monto)** (f1_macro = {formatear_media_std(resultado_log_monto['resumen'], 'f1_macro')}), "
        f"se usa **{monto_elegido}** en '+todas las features' porque obtuvo el f1_macro medio mas alto "
        f"(se descarta {monto_descartado} para esa fila combinada)."
    )

    md = f"""# Benchmark "solo texto" vs. "texto + features adicionales" (Fase 10)

Dataset: `{args.datos}`
Filas entrenables: {len(entrenables):,} | Comercios unicos: {entrenables['comercio'].nunique()}
Split: `StratifiedGroupKFold(n_splits={N_SPLITS}, shuffle=True, random_state={args.semilla})`
agrupado por `comercio`, estratificado por `categoria` (igual que las Fases 2 y 9).

Base: el pipeline vigente (palabra+caracter TFIDF + `LinearSVC` calibrado), que
en la Fase 9 no fue superado con confianza por ningun otro vectorizador/clasificador
clasico (ver `ciencia-datos/experimentos/benchmark_clasico.md`). Esta fase parte de
ese mismo pipeline y le agrega bloques de features numericas/categoricas via
`ColumnTransformer`, sin usar nada derivado de la categoria real.

## Features probadas

- `monto` y `log1p(monto)` (columna "monto", siempre > 0 en este dataset).
- `longitud_texto` = `len(descripcion_limpia)`.
- flags binarios `flag_<token>` para {", ".join(TOKENS_PREFIJO)}, buscados en la
  columna **"descripcion" original** (sin limpiar), porque `normalizar_texto()`
  los quita a proposito al construir `descripcion_limpia`.
  Frecuencia de cada flag en el conjunto entrenable:
{chr(10).join(f"  - `flag_{t}`: {int(entrenables[f'flag_{t}'].sum()):,} filas ({entrenables[f'flag_{t}'].mean() * 100:.2f}%)" for t in TOKENS_PREFIJO)}
- `dia_semana` (0-6) y `mes` (1-12) de la columna "fecha", codificados con
  `OneHotEncoder` (categoricas, no ordinales/ciclicas de verdad).

Todas las numericas se escalan con `StandardScaler`; el texto sigue vectorizado
con TF-IDF palabra (1,2-gram) + caracter (char_wb 3-5), exactamente como en el
pipeline vigente. Se combinan con `sklearn.compose.ColumnTransformer`.

## Resultados (filas nuevas de esta fase, en el orden en que se corrieron)

{tabla_markdown(tabla_comparacion)}

## Control (solo texto)

accuracy = {formatear_media_std(control['resumen'], 'accuracy')},
f1_macro = {formatear_media_std(control['resumen'], 'f1_macro')},
f1_weighted = {formatear_media_std(control['resumen'], 'f1_weighted')},
balanced_accuracy = {formatear_media_std(control['resumen'], 'balanced_accuracy')}.
(Deberia salir igual o muy cercano al candidato "actual" de la Fase 9 y a la
Fase 2, porque es el mismo pipeline sobre el mismo split.)

## monto vs. log1p(monto)

{lineas_monto}

## Cuanto aporta (o no) cada bloque de features, frente al control de solo texto

{chr(10).join(lineas_ablacion)}
- **+todas las features (monto: {monto_elegido})**: f1_macro = {formatear_media_std(resultado_todas['resumen'], 'f1_macro')} (delta vs. control = {signo_todas}{delta_todas:.4f}) -> {veredicto_todas}.

## Conclusion

Se consideran equivalentes ("dentro de 1 desviacion estandar") aquellos bloques
cuyo rango media +/- desviacion estandar de f1_macro se solapa con el del control
de solo texto; en ese caso la diferencia observada puede deberse a la variabilidad
entre folds y no a una ventaja real de agregar esa feature. Si ninguna combinacion
(incluida "+todas las features") supera al control fuera de ese margen, la
recomendacion es **mantener el pipeline de solo texto**: es mas simple, mas rapido
de entrenar/servir y evita depender de columnas (monto, fecha, prefijos de extracto)
que pueden no estar disponibles o tener otro formato en produccion.
"""

    args.salida_md.parent.mkdir(parents=True, exist_ok=True)
    with open(args.salida_md, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"Guardado MD en {args.salida_md}")


if __name__ == "__main__":
    main()
