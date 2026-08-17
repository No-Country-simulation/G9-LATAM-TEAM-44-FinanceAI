"""
Módulo centralizado y reutilizable para la extracción de features.
Cumple con el requerimiento del Día 6:
- Texto: TF-IDF de caracteres (char_wb, n-gramas 3 a 5).
- Tabular: Ratios financieros acotados para el modelo de perfil.
"""

import re
import unicodedata
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

# 1. PIPELINE DE LIMPIEZA Y FEATURES DE TEXTO (TRANSACCIONES)
def limpiar_texto(texto: str) -> str:
    """Normaliza el texto: minúsculas, sin tildes ni dígitos."""
    if not isinstance(texto, str):
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    texto = re.sub(r'[^a-z\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def obtener_vectorizador_texto() -> TfidfVectorizer:
    """TF-IDF configurado: char_wb de 3 a 5 caracteres."""
    return TfidfVectorizer(
        analyzer='char_wb',
        ngram_range=(3, 5),
        preprocessor=limpiar_texto,
        min_df=2
    )

# 2. INGENIERÍA DE FEATURES TABULARES (PERFIL FINANCIERO)
def calcular_features_tabulares(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula y estandariza las 4 métricas tabulares exigidas."""
    df_feat = df.copy()

    # 1. Ratio deuda / ingreso
    if 'ratio_deuda' not in df_feat.columns and 'deuda_total' in df_feat.columns:
        df_feat['ratio_deuda'] = (df_feat['deuda_total'] / df_feat['ingreso']).clip(0.0, 2.0)
    elif 'ratio_deuda' in df_feat.columns:
        df_feat['ratio_deuda'] = df_feat['ratio_deuda'].clip(0.0, 2.0)

    # 2. Tasa de gasto total / ingreso
    if 'tasa_gasto' not in df_feat.columns and 'gasto_total' in df_feat.columns:
        df_feat['tasa_gasto'] = (df_feat['gasto_total'] / df_feat['ingreso']).clip(0.0, 3.0)
    elif 'tasa_gasto' in df_feat.columns:
        df_feat['tasa_gasto'] = df_feat['tasa_gasto'].clip(0.0, 3.0)

    # 3. Porcentaje de gasto esencial
    if 'pct_gasto_esencial' not in df_feat.columns:
        if 'gasto_esencial' in df_feat.columns and 'gasto_total' in df_feat.columns:
            df_feat['pct_gasto_esencial'] = (df_feat['gasto_esencial'] / df_feat['gasto_total']).fillna(0.0)
        else:
            df_feat['pct_gasto_esencial'] = 0.5
    df_feat['pct_gasto_esencial'] = df_feat['pct_gasto_esencial'].clip(0.0, 1.0)

    # 4. Concentración de ahorro
    if 'concentracion_gasto' not in df_feat.columns:
        if 'frecuencia_ahorro' in df_feat.columns:
            df_feat['concentracion_gasto'] = (df_feat['frecuencia_ahorro'] / 15.0).clip(0.0, 1.0)
        else:
            df_feat['concentracion_gasto'] = 0.5

    columnas_finales = ['ingreso', 'ratio_deuda', 'tasa_gasto', 'pct_gasto_esencial', 'concentracion_gasto']
    return df_feat[columnas_finales]
