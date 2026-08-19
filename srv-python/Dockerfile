# ml-service.
#
# El contexto de build es la raiz del repositorio, no srv-python/, porque la
# imagen necesita features.py y oci_storage.py, que viven en ciencia-datos/ y
# se comparten con el notebook.
#
#   docker build -f srv-python/Dockerfile .
FROM python:3.12-slim

WORKDIR /srv

# Las dependencias primero: cambian mucho menos que el codigo, asi la capa de
# pip se reutiliza entre builds.
COPY srv-python/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY srv-python/app ./app

# Los modulos compartidos viajan dentro del paquete. modelos.py y reglas.py
# buscan primero en app/ciencia_datos y por eso funciona igual dentro del
# contenedor que en local.
COPY ciencia-datos/features.py ciencia-datos/oci_storage.py ./app/ciencia_datos/

# Los artefactos NO se copian a la imagen: se descargan de OCI Object Storage
# al arrancar. Asi se publica un modelo nuevo sin reconstruir ni redesplegar.
# Si OCI no esta configurado, monta ciencia-datos/artefactos como volumen:
#   -v ./ciencia-datos/artefactos:/srv/artefactos
ENV RUTA_ARTEFACTOS=/srv/artefactos

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
