import os
import json
import re
import pandas as pd

# CONFIGURACIÓN DE RUTAS
CARPETA_ENTRADA = "archivos_financieros_usuarios"
CARPETA_SALIDA = "archivos_financieros_limpios"

if not os.path.exists(CARPETA_SALIDA):
    os.makedirs(CARPETA_SALIDA)

# FUNCIONES DE LIMPIEZA
def limpiar_descripcion(texto):
    """Limpia caracteres basura, corrige espacios y estandariza mayúsculas/minúsculas."""
    if pd.isna(texto) or texto is None or str(texto).strip() == "":
        return "Desconocido"
    
    texto = str(texto)
    patrones_basura = [r"TRF/POS", r"ERR:", r"#", r"\*", r"\$\$", r"%", r"///", r"---"]
    for patron in patrones_basura:
        texto = re.sub(patron, "", texto, flags=re.IGNORECASE)
    
    texto = " ".join(texto.split())
    texto = texto.title()
    
    return texto if texto else "Desconocido"

def limpiar_fecha(fecha_str):
    """Estandariza la fecha a formato YYYY-MM-DD usando la capacidad de inferencia de Pandas."""
    if pd.isna(fecha_str) or fecha_str is None or str(fecha_str).strip() == "":
        return "1900-01-01" # Fecha por defecto para nulos
    
    fecha_str = str(fecha_str).strip()
    
    try:
        # formato DD/MM/YYYY
        fecha_obj = pd.to_datetime(fecha_str, format='mixed', dayfirst=True)
        return fecha_obj.strftime("%Y-%m-%d")
        
    except Exception:
        # Si la fecha está corrupta
        return "1900-01-01"

# PROCESAMIENTO, ORDENAMIENTO Y CONVERSIÓN
archivos = [f for f in os.listdir(CARPETA_ENTRADA) if f.endswith(('.json', '.csv', '.xlsx'))]

print(f"Iniciando limpieza y conversión a JSON de {len(archivos)} archivos...\n")

for archivo in archivos:
    ruta_entrada = os.path.join(CARPETA_ENTRADA, archivo)
    nombre, extension = os.path.splitext(archivo)
    extension = extension.lower()
    
    ruta_salida = os.path.join(CARPETA_SALIDA, f"{nombre}.json")
    
    try:
        # PROCESAR ARCHIVOS JSON ORIGINALES
        if extension == '.json':
            with open(ruta_entrada, 'r', encoding='utf-8') as f:
                datos_json = json.load(f)
            
            # Limpiar datos
            for tx in datos_json:
                tx["descripcion"] = limpiar_descripcion(tx.get("descripcion"))
                tx["fecha"] = limpiar_fecha(tx.get("fecha"))
                tx["monto"] = abs(float(tx.get("monto", 0.0)))
            
            # Ordenar
            datos_json = sorted(datos_json, key=lambda x: x["fecha"])

        # PROCESAR ARCHIVOS CSV Y EXCEL
        elif extension in ['.csv', '.xlsx']:
            if extension == '.csv':
                df = pd.read_csv(ruta_entrada)
            else:
                df = pd.read_excel(ruta_entrada)
            
            # Limpiar datos
            df["descripcion"] = df["descripcion"].apply(limpiar_descripcion)
            df["fecha"] = df["fecha"].apply(limpiar_fecha)
            df["monto"] = df["monto"].abs()
            
            # Ordenar transacciones
            df = df.sort_values(by="fecha", ascending=True).reset_index(drop=True)
            datos_json = df.to_dict(orient='records')
            
        # GUARDAR RESULTADO (SIEMPRE COMO JSON)
        with open(ruta_salida, 'w', encoding='utf-8') as f:
            json.dump(datos_json, f, ensure_ascii=False, indent=2)
            
        print(f"Limpio y convertido ({extension.upper()[1:]} -> JSON): {nombre}.json")

    except Exception as e:
        print(f"Error al procesar {archivo}: {str(e)}")

print(f"\n ¡Proceso completado! Todos los archivos están limpios, ordenados y en formato JSON dentro de '{CARPETA_SALIDA}'.")