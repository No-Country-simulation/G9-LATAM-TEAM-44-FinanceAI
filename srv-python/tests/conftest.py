"""Configuracion de pytest para el ml-service.

Pone en sys.path la raiz de srv-python (para `import app...`) y ciencia-datos
(para `import features` / `import oci_storage`). Sin esto, que las pruebas
pasen dependeria del orden de los imports dentro de cada archivo.
"""
import sys
from pathlib import Path

RAIZ_SRV = Path(__file__).resolve().parent.parent
CIENCIA_DATOS = RAIZ_SRV.parent / "ciencia-datos"
EMPAQUETADO = RAIZ_SRV / "app" / "ciencia_datos"  # copia dentro de la imagen Docker

for ruta in (RAIZ_SRV, CIENCIA_DATOS if CIENCIA_DATOS.exists() else EMPAQUETADO):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))
