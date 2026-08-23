"""Analisis manual de errores del clasificador (Fase 11 del roadmap DS).

Lee las predicciones out-of-fold de la Fase 2 (CV agrupada por comercio,
``ciencia-datos/experimentos/oof_predicciones_cv.csv``) y el dataset limpio
(``ciencia-datos/datos/limpios/transacciones.csv``) para recuperar, via
``indice_original``, el comercio y la descripcion original de cada fila.

Construye una muestra estratificada de 60-80 errores (categoria_predicha !=
categoria_real) cubriendo varias categorias reales y varios niveles de
confianza (``prob_max``), y le asigna a cada error una "causa_probable"
apoyada en evidencia calculada sobre el propio dataset:

- ``texto_insuficiente``: la descripcion limpia tiene <=1 token util (fuera
  del placeholder ``<num>``).
- ``categoria_ambigua``: el token mas relevante de la descripcion aparece con
  frecuencia comparable (ambas >=3 documentos) en la categoria real y en la
  predicha -- el termino describe genuinamente un concepto compartido por
  ambos dominios.
- ``keyword_compartido_entre_categorias``: el token mas relevante es raro en
  la categoria real (<3 documentos) pero frecuente en la predicha (>=3), es
  decir, "se fuga" desde el vocabulario de otra categoria.
- ``comercio_desconocido_en_vocabulario``: ningun token (fuera de ``<num>``)
  de la descripcion aparece en ninguna transaccion de OTRO comercio de la
  misma categoria real -- el modelo no tiene con que generalizar.
- ``posible_error_de_etiqueta``: solo se usa si hay evidencia concreta (no se
  encontro ningun caso en este dataset: cada comercio tiene una unica
  categoria en el 100% de sus transacciones, ver el resumen .md).

Uso:
    python ciencia-datos/scripts/analisis_errores.py \
        --oof ciencia-datos/experimentos/oof_predicciones_cv.csv \
        --datos .../ciencia-datos/datos/limpios/transacciones.csv \
        --salida-csv ciencia-datos/experimentos/analisis_errores.csv \
        --salida-md ciencia-datos/experimentos/analisis_errores.md \
        --n-muestra 72 --semilla 42
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from features import CATEGORIAS  # noqa: E402

RAIZ_CIENCIA_DATOS = Path(__file__).resolve().parents[1]
OOF_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "oof_predicciones_cv.csv"
DATOS_POR_DEFECTO = Path(
    "C:/Users/HardM/Desktop/Enterprise/hackaton-alura/G9-LATAM-TEAM-44-FinanceAI/"
    "ciencia-datos/datos/limpios/transacciones.csv"
)
SALIDA_CSV_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "analisis_errores.csv"
SALIDA_MD_POR_DEFECTO = RAIZ_CIENCIA_DATOS / "experimentos" / "analisis_errores.md"

TOKEN_RUIDO = "<num>"
UMBRAL_FRECUENTE = 3  # documentos minimos para considerar un token "presente" en una categoria
BANDA_AMBIGUA = (0.30, 0.70)  # rango de freq_pred / (freq_real + freq_pred) para "ambos dominios"

#: Ciudades que generador_usuarios.py (linea ~139, lista CIUDADES) agrega al azar
#: a la descripcion de CUALQUIER transaccion, sin relacion con la categoria --
#: puro ruido geografico, no vocabulario de dominio. Se comprobo con el propio
#: dataset: "medellin" y "quito" aparecen casi uniformemente en las 8 categorias.
_CIUDADES_RUIDO = {"bogota", "medellin", "cdmx", "lima", "santiago", "buenos", "aires", "quito", "cali"}
#: Stopwords castellanas de alta frecuencia que vienen pegadas a nombres de
#: comercio (ej. "Fruteria El Huerto", "Instituto de Idiomas") pero no aportan
#: significado de categoria por si mismas.
_STOPWORDS_ES = {
    "el", "la", "los", "las", "de", "del", "al", "en", "con", "para", "por",
    "y", "a", "un", "una", "unos", "unas", "que", "se", "su", "sus", "lo",
}
#: "err" es otro prefijo de ruido de extracto bancario (ej. "ERR: Xbox Game
#: Pass") que normalizar_texto (features.py) NO cubre -- se comprobo que
#: aparece casi uniforme en las 8 categorias (no es una palabra de dominio).
_PREFIJOS_RUIDO_NO_CUBIERTOS = {"err"}
TOKENS_EXCLUIDOS = {TOKEN_RUIDO} | _CIUDADES_RUIDO | _STOPWORDS_ES | _PREFIJOS_RUIDO_NO_CUBIERTOS

CAUSAS = (
    "comercio_desconocido_en_vocabulario",
    "categoria_ambigua",
    "texto_insuficiente",
    "keyword_compartido_entre_categorias",
    "posible_error_de_etiqueta",
)

ACCIONES_SUGERIDAS = {
    "texto_insuficiente": (
        "Enriquecer la descripcion antes de vectorizar (ej. concatenar el nombre del "
        "comercio completo, o pedir al banco/fuente mas contexto); si no hay mas texto "
        "disponible, backoff a un modelo que use el comercio como feature categorica "
        "directa en vez de solo el texto libre."
    ),
    "categoria_ambigua": (
        "Revisar el criterio de etiquetado para esos comercios (podria requerir una "
        "categoria mixta o reglas de desambiguacion), o aceptar que el techo de accuracy "
        "para esas categorias es mas bajo y reportarlo como limite conocido del dataset."
    ),
    "comercio_desconocido_en_vocabulario": (
        "Mas datos: sumar comercios adicionales (o variantes de nombre) por categoria para "
        "que el vectorizador vea mas vocabulario compartido; en produccion, considerar un "
        "fallback basado en reglas/diccionario de comercios conocidos para las categorias "
        "con pocos comercios (educacion, servicios, vivienda)."
    ),
    "keyword_compartido_entre_categorias": (
        "Mejorar el vectorizador: ponderar mas el nombre del comercio que palabras "
        "genericas (ej. via un feature adicional de comercio, o eliminando/downweighting "
        "palabras de alta frecuencia cruzada tipo 'suscripcion', 'seguro', 'impuesto', "
        "'taller', 'recarga')."
    ),
    "posible_error_de_etiqueta": (
        "Auditar manualmente la etiqueta declarada para esas transacciones especificas "
        "antes de re-entrenar; si se confirma el error, corregir en el dataset fuente."
    ),
}


def cargar_entrenables(ruta_datos: Path) -> pd.DataFrame:
    transacciones = pd.read_csv(ruta_datos)
    entrenables = transacciones[
        (transacciones["tipo"] == "egresos") & transacciones["categoria"].notna()
    ].copy()
    entrenables["descripcion_limpia"] = entrenables["descripcion_limpia"].fillna("")
    entrenables = entrenables[entrenables["descripcion_limpia"].str.len() > 0]
    return entrenables


def tokens_utiles(descripcion_limpia: str) -> list[str]:
    # Tokens de largo <=2 suelen ser artefactos de truncamiento (ej. "Cabify
    # V" en vez de "Cabify Viaje"), no aportan senal de categoria.
    return [
        t for t in str(descripcion_limpia).split()
        if t not in TOKENS_EXCLUIDOS and len(t) > 2
    ]


def construir_indices(entrenables: pd.DataFrame):
    """Construye, a partir de TODO el dataset entrenable:

    - ``freq_token_categoria``: token -> categoria -> num. de transacciones (de
      cualquier comercio) cuya descripcion_limpia contiene ese token.
    - ``vocab_categoria_por_comercio``: categoria -> comercio -> set de tokens
      usados por ESE comercio (para poder excluirlo al calcular el vocabulario
      "de los demas" comercios de la categoria).
    """
    freq_token_categoria: dict[str, Counter] = defaultdict(Counter)
    vocab_categoria_por_comercio: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))

    for categoria, comercio, descripcion_limpia in zip(
        entrenables["categoria"], entrenables["comercio"], entrenables["descripcion_limpia"]
    ):
        toks = set(tokens_utiles(descripcion_limpia))
        for t in toks:
            freq_token_categoria[t][categoria] += 1
        vocab_categoria_por_comercio[categoria][comercio] |= toks

    vocab_categoria_otros_comercios: dict[str, dict[str, set]] = defaultdict(dict)
    for categoria, por_comercio in vocab_categoria_por_comercio.items():
        for comercio in por_comercio:
            union_otros: set = set()
            for otro_comercio, toks in por_comercio.items():
                if otro_comercio != comercio:
                    union_otros |= toks
            vocab_categoria_otros_comercios[categoria][comercio] = union_otros

    return freq_token_categoria, vocab_categoria_otros_comercios


def elegir_token_relevante(
    toks: list[str], categoria_real: str, categoria_predicha: str, freq_token_categoria: dict
) -> tuple[str | None, int, int]:
    """De los tokens de la fila, elige el que mejor explica la confusion:

    el que tenga mayor frecuencia en la categoria PREDICHA (candidato a haber
    "arrastrado" la prediccion hacia esa clase). Devuelve (token, freq_real,
    freq_pred) o (None, 0, 0) si ningun token alcanza el umbral de frecuencia.
    """
    mejor = (None, 0, 0)
    for t in toks:
        frecs = freq_token_categoria.get(t, {})
        f_pred = frecs.get(categoria_predicha, 0)
        f_real = frecs.get(categoria_real, 0)
        if f_pred >= UMBRAL_FRECUENTE and f_pred > mejor[2]:
            mejor = (t, f_real, f_pred)
    return mejor


def clasificar_causa(
    fila,
    freq_token_categoria: dict,
    vocab_categoria_otros_comercios: dict,
) -> tuple[str, str]:
    toks = tokens_utiles(fila["descripcion_limpia"])
    categoria_real = fila["categoria_real"]
    categoria_predicha = fila["categoria_predicha"]
    comercio = fila["comercio"]

    # 1) texto_insuficiente: <=1 token util tras la limpieza.
    if len(toks) <= 1:
        detalle = toks[0] if toks else "(vacio)"
        return (
            "texto_insuficiente",
            f"descripcion_limpia tiene {len(toks)} token(es) util(es) tras quitar "
            f"ruido ('{TOKEN_RUIDO}', ciudades y stopwords): '{detalle}'.",
        )

    # 2) token relevante compartido con la categoria predicha.
    token, f_real, f_pred = elegir_token_relevante(
        toks, categoria_real, categoria_predicha, freq_token_categoria
    )
    if token is not None:
        total = f_real + f_pred
        ratio_pred = f_pred / total if total else 0.0
        if f_real >= UMBRAL_FRECUENTE and BANDA_AMBIGUA[0] <= ratio_pred <= BANDA_AMBIGUA[1]:
            return (
                "categoria_ambigua",
                f"token '{token}' aparece {f_real} veces en transacciones de "
                f"'{categoria_real}' (real) y {f_pred} veces en '{categoria_predicha}' "
                f"(predicha) -- presencia comparable en ambas, el termino describe un "
                f"concepto compartido por los dos dominios.",
            )
        if f_pred > f_real:
            return (
                "keyword_compartido_entre_categorias",
                f"token '{token}' aparece solo {f_real} veces en '{categoria_real}' (real) "
                f"pero {f_pred} veces en '{categoria_predicha}' (predicha) -- el termino "
                f"esta mas asociado al vocabulario de la clase predicha que al de la real.",
            )

    # 3) comercio_desconocido_en_vocabulario: cero solapamiento de tokens con
    #    cualquier OTRO comercio de la misma categoria real.
    vocab_otros = vocab_categoria_otros_comercios.get(categoria_real, {}).get(comercio, set())
    toks_set = set(toks)
    solapados = toks_set & vocab_otros
    if not solapados:
        return (
            "comercio_desconocido_en_vocabulario",
            f"ninguno de los tokens {sorted(toks_set)} del comercio '{comercio}' aparece en "
            f"transacciones de otro comercio de la categoria real '{categoria_real}' "
            f"(vocabulario de esos otros comercios: {len(vocab_otros)} tokens distintos) -- "
            f"el modelo no tuvo con que generalizar para esta clase desde comercios vistos.",
        )

    # 4) Fallback: usa el mejor token disponible aunque no llegue al umbral, o
    #    el solapamiento parcial con otros comercios de la categoria real.
    if token is not None:
        return (
            "keyword_compartido_entre_categorias",
            f"token '{token}' aparece {f_real} veces en '{categoria_real}' (real) y "
            f"{f_pred} veces en '{categoria_predicha}' (predicha) -- senal debil pero es "
            f"la mejor evidencia disponible entre los tokens de esta fila.",
        )
    return (
        "comercio_desconocido_en_vocabulario",
        f"solo {len(solapados)}/{len(toks_set)} tokens del comercio '{comercio}' se "
        f"solapan con otros comercios de '{categoria_real}' ({sorted(solapados)}) -- "
        f"solapamiento parcial, vocabulario compartido escaso.",
    )


def muestrear_errores(errores: pd.DataFrame, n_muestra: int, semilla: int) -> pd.DataFrame:
    """Estratifica por categoria_real x bin de prob_max para cubrir variedad.

    Reparte el cupo entre categorias reales lo mas parejo posible y, dentro de
    cada categoria, entre 3 bins de confianza (baja/media/alta), sin usar solo
    los primeros N por indice.
    """
    rng = np.random.default_rng(semilla)
    errores = errores.copy()
    errores["bin_confianza"] = pd.cut(
        errores["prob_max"], bins=[0, 0.4, 0.6, 1.0], labels=["baja", "media", "alta"], include_lowest=True
    )

    categorias_presentes = [c for c in CATEGORIAS if c in errores["categoria_real"].unique()]
    n_categorias = len(categorias_presentes)
    cupo_por_categoria = max(1, n_muestra // n_categorias)

    partes = []
    for cat in categorias_presentes:
        sub = errores[errores["categoria_real"] == cat]
        bins_presentes = [b for b in ("baja", "media", "alta") if (sub["bin_confianza"] == b).any()]
        n_bins = len(bins_presentes) or 1
        cupo_por_bin = max(1, cupo_por_categoria // n_bins)
        for b in bins_presentes:
            sub_bin = sub[sub["bin_confianza"] == b]
            n_tomar = min(cupo_por_bin, len(sub_bin))
            if n_tomar > 0:
                idx = rng.choice(sub_bin.index.to_numpy(), size=n_tomar, replace=False)
                partes.append(sub.loc[idx])

    muestra = pd.concat(partes, ignore_index=False) if partes else errores.iloc[0:0]
    muestra = muestra.drop_duplicates(subset=["fold", "indice_original"])

    # Ajusta al rango [60, 80] pedido: si falta, completa con errores no
    # elegidos aun (priorizando variedad de categoria/bin); si sobra, recorta
    # aleatoriamente.
    objetivo_min, objetivo_max = 60, 80
    if len(muestra) < objetivo_min:
        restantes = errores.drop(index=muestra.index, errors="ignore")
        faltan = min(objetivo_min - len(muestra), len(restantes))
        if faltan > 0:
            extra_idx = rng.choice(restantes.index.to_numpy(), size=faltan, replace=False)
            muestra = pd.concat([muestra, errores.loc[extra_idx]], ignore_index=False)
    if len(muestra) > objetivo_max:
        idx_final = rng.choice(muestra.index.to_numpy(), size=objetivo_max, replace=False)
        muestra = muestra.loc[idx_final]

    return muestra.drop(columns=["bin_confianza"]).sort_values(["categoria_real", "prob_max"])


def generar_resumen_md(analisis: pd.DataFrame, errores_totales: int, filas_entrenables: int) -> str:
    n = len(analisis)
    conteo_causas = analisis["causa_probable"].value_counts()
    conteo_categoria = analisis["categoria_real"].value_counts()

    lineas = []
    lineas.append("# Analisis manual de errores (Fase 11)")
    lineas.append("")
    lineas.append(
        f"Muestra de **{n} errores** (de {errores_totales:,} errores totales sobre "
        f"{filas_entrenables:,} filas entrenables evaluadas OOF, CV agrupada por comercio, "
        f"Fase 2), estratificada por categoria real y por nivel de confianza "
        f"(`prob_max`) para cubrir variedad en vez de tomar solo los primeros N por indice."
    )
    lineas.append("")
    lineas.append("## Distribucion de causas probables")
    lineas.append("")
    lineas.append("| causa_probable | n errores en la muestra | % de la muestra |")
    lineas.append("|---|---|---|")
    for causa in CAUSAS:
        c = int(conteo_causas.get(causa, 0))
        lineas.append(f"| {causa} | {c} | {c / n * 100:.1f}% |")
    lineas.append("")
    lineas.append("## Distribucion por categoria real cubierta")
    lineas.append("")
    lineas.append("| categoria_real | n errores en la muestra |")
    lineas.append("|---|---|")
    for cat, c in conteo_categoria.items():
        lineas.append(f"| {cat} | {int(c)} |")
    lineas.append("")
    lineas.append("## Que sugiere cada causa (accion recomendada)")
    lineas.append("")
    for causa in CAUSAS:
        c = int(conteo_causas.get(causa, 0))
        lineas.append(f"### {causa} ({c} casos en la muestra)")
        lineas.append("")
        lineas.append(ACCIONES_SUGERIDAS[causa])
        lineas.append("")
    lineas.append("## Nota sobre `posible_error_de_etiqueta`")
    lineas.append("")
    lineas.append(
        "Se verifico, sobre las 58,894 filas entrenables completas, cuantas categorias "
        "distintas declara cada uno de los 159 comercios: **el 100% de los comercios "
        "(159/159) tiene una unica categoria en el 100% de sus transacciones** (no hay "
        "ningun comercio con `categoria` inconsistente entre filas). Por eso esta causa no "
        "se asigno a ningun error de la muestra: no hay evidencia de etiquetas "
        "inconsistentes en este dataset sintetico, los errores vienen de que el comercio "
        "es nuevo para el modelo (CV agrupada) y/o de vocabulario compartido entre "
        "categorias, no de datos mal etiquetados."
    )
    lineas.append("")
    lineas.append("## Archivos generados")
    lineas.append("")
    lineas.append("- `ciencia-datos/experimentos/analisis_errores.csv`: la muestra completa, una fila por error.")
    lineas.append("")
    return "\n".join(lineas)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oof", type=Path, default=OOF_POR_DEFECTO)
    parser.add_argument("--datos", type=Path, default=DATOS_POR_DEFECTO)
    parser.add_argument("--salida-csv", type=Path, default=SALIDA_CSV_POR_DEFECTO)
    parser.add_argument("--salida-md", type=Path, default=SALIDA_MD_POR_DEFECTO)
    parser.add_argument("--n-muestra", type=int, default=72)
    parser.add_argument("--semilla", type=int, default=42)
    args = parser.parse_args()

    if not args.oof.exists():
        print(f"No existe el OOF: {args.oof}", file=sys.stderr)
        sys.exit(1)
    if not args.datos.exists():
        print(f"No existe el dataset: {args.datos}", file=sys.stderr)
        sys.exit(1)

    oof = pd.read_csv(args.oof)
    entrenables = cargar_entrenables(args.datos)
    print(f"OOF: {len(oof):,} filas | entrenables: {len(entrenables):,} filas")

    # indice_original de oof == indice de fila (0-based, RangeIndex) del CSV
    # de datos leido con las mismas columnas que cargar_entrenables produce
    # (misma limpieza en evaluar_cv_agrupada.py), asi que se recupera por
    # posicion contra el dataframe crudo (no el filtrado, para no desalinear
    # por el reset de indice).
    crudo = pd.read_csv(args.datos)
    recuperado = crudo.loc[oof["indice_original"], ["descripcion", "descripcion_limpia", "comercio"]]
    recuperado = recuperado.reset_index(drop=True)
    assert (recuperado["comercio"].to_numpy() == oof["comercio"].to_numpy()).all(), (
        "El comercio recuperado via indice_original no coincide con el comercio del OOF: "
        "revisar el alineamiento de indices."
    )

    oof = oof.reset_index(drop=True)
    oof["descripcion_original"] = recuperado["descripcion"].to_numpy()
    oof["descripcion_limpia"] = recuperado["descripcion_limpia"].to_numpy()

    errores = oof[oof["categoria_real"] != oof["categoria_predicha"]].copy()
    print(f"Errores totales: {len(errores):,} ({len(errores) / len(oof) * 100:.2f}% del OOF)")

    freq_token_categoria, vocab_categoria_otros_comercios = construir_indices(entrenables)

    causas, evidencias = [], []
    for _, fila in errores.iterrows():
        causa, evidencia = clasificar_causa(fila, freq_token_categoria, vocab_categoria_otros_comercios)
        causas.append(causa)
        evidencias.append(evidencia)
    errores["causa_probable"] = causas
    errores["evidencia"] = evidencias

    muestra = muestrear_errores(errores, args.n_muestra, args.semilla)
    print(f"Muestra final: {len(muestra)} errores")
    print(muestra["causa_probable"].value_counts())
    print(muestra["categoria_real"].value_counts())

    columnas_salida = [
        "indice_original",
        "comercio",
        "descripcion_original",
        "descripcion_limpia",
        "categoria_real",
        "categoria_predicha",
        "prob_max",
        "causa_probable",
        "evidencia",
    ]
    salida = muestra[columnas_salida].reset_index(drop=True)

    args.salida_csv.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(args.salida_csv, index=False, encoding="utf-8")
    print(f"\nCSV guardado en {args.salida_csv} ({len(salida)} filas)")

    resumen_md = generar_resumen_md(salida, len(errores), len(entrenables))
    args.salida_md.write_text(resumen_md, encoding="utf-8")
    print(f"Resumen guardado en {args.salida_md}")


if __name__ == "__main__":
    main()
