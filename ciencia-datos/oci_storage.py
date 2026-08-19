"""Cliente de OCI Object Storage para los artefactos de modelo.

Lo usan el notebook (sube los modelos entrenados) y srv-python (los descarga
al arrancar).

Dos formas de autenticarse, se prueban en este orden:

  1. SDK `oci`, con ~/.oci/config en local o instance principals dentro de
     OCI Compute.
  2. Pre-Authenticated Request (PAR): una URL firmada con caducidad. Solo
     necesita urllib.

Sin ninguna de las dos, las funciones devuelven False en lugar de lanzar, para
que el servicio pueda arrancar con los artefactos locales.

Variables de entorno:
    OCI_BUCKET        nombre del bucket           (ej. finance-ai-models)
    OCI_NAMESPACE     namespace de Object Storage (ej. axhelop1abcd)
    OCI_REGION        region                      (ej. us-ashburn-1)
    OCI_PREFIJO       prefijo/carpeta opcional    (ej. modelos/v1)
    OCI_AUTH          config_file | instance_principal | resource_principal
    OCI_CONFIG_FILE   ruta al config del SDK      (def. ~/.oci/config)
    OCI_PROFILE       perfil dentro del config    (def. DEFAULT)
    OCI_PAR_URL       URL de PAR terminada en /   (alternativa al SDK)
"""
from __future__ import annotations

import logging
import os
import urllib.error
import urllib.request
from typing import Optional

log = logging.getLogger(__name__)

TIEMPO_ESPERA = int(os.getenv("OCI_TIMEOUT", "30"))


# ------------------------------------------------------------------ config

def _bucket() -> Optional[str]:
    return os.getenv("OCI_BUCKET") or None


def _namespace() -> Optional[str]:
    return os.getenv("OCI_NAMESPACE") or None


def _par_url() -> Optional[str]:
    url = os.getenv("OCI_PAR_URL")
    if not url:
        return None
    return url if url.endswith("/") else url + "/"


def _ruta_objeto(nombre: str) -> str:
    """Antepone OCI_PREFIJO al nombre del objeto, si esta definido."""
    prefijo = (os.getenv("OCI_PREFIJO") or "").strip("/")
    return f"{prefijo}/{nombre}" if prefijo else nombre


def _cliente_sdk():
    """ObjectStorageClient, o None si el SDK no esta instalado o configurado."""
    try:
        import oci  # opcional, por eso el import va aqui dentro
    except ImportError:
        return None

    modo = (os.getenv("OCI_AUTH") or "config_file").lower()
    try:
        if modo == "instance_principal":
            firmante = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            return oci.object_storage.ObjectStorageClient({}, signer=firmante)
        if modo == "resource_principal":
            firmante = oci.auth.signers.get_resource_principals_signer()
            return oci.object_storage.ObjectStorageClient({}, signer=firmante)

        ruta = os.getenv("OCI_CONFIG_FILE") or oci.config.DEFAULT_LOCATION
        perfil = os.getenv("OCI_PROFILE") or "DEFAULT"
        if not os.path.exists(os.path.expanduser(ruta)):
            return None
        config = oci.config.from_file(ruta, perfil)
        if os.getenv("OCI_REGION"):
            config["region"] = os.getenv("OCI_REGION")
        return oci.object_storage.ObjectStorageClient(config)
    except Exception as e:  # credenciales incompletas, perfil inexistente, etc.
        log.warning("No se pudo inicializar el cliente de OCI (%s): %s", type(e).__name__, e)
        return None


def configurado() -> bool:
    """True si hay alguna via de acceso lista para usarse."""
    if _par_url():
        return True
    return bool(_bucket() and _namespace() and _cliente_sdk() is not None)


def describir() -> dict:
    """Configuracion activa, tal como se expone en /modelo/info."""
    via = "par" if _par_url() else ("sdk" if configurado() else "no_configurado")
    return {
        "via": via,
        "bucket": _bucket(),
        "namespace": _namespace(),
        "region": os.getenv("OCI_REGION"),
        "prefijo": os.getenv("OCI_PREFIJO") or None,
    }


def uri(nombre: str) -> str:
    """URI canonica del objeto."""
    bucket = _bucket() or "finance-ai-models"
    return f"oci://{bucket}/{_ruta_objeto(nombre)}"


# ------------------------------------------------------------------ subida

def subir(ruta_local: str, nombre_objeto: str) -> bool:
    """Sube un archivo local al bucket. Devuelve True si quedo almacenado."""
    if not os.path.exists(ruta_local):
        log.error("No existe el archivo a subir: %s", ruta_local)
        return False

    objeto = _ruta_objeto(nombre_objeto)

    cliente = _cliente_sdk()
    if cliente and _bucket() and _namespace():
        try:
            with open(ruta_local, "rb") as f:
                cliente.put_object(_namespace(), _bucket(), objeto, f)
            log.info("Subido a %s", uri(nombre_objeto))
            return True
        except Exception as e:
            log.error("Fallo la subida por SDK (%s): %s", type(e).__name__, e)

    par = _par_url()
    if par:
        try:
            with open(ruta_local, "rb") as f:
                datos = f.read()
            peticion = urllib.request.Request(par + objeto, data=datos, method="PUT")
            peticion.add_header("Content-Type", "application/octet-stream")
            with urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA) as r:
                if 200 <= r.status < 300:
                    log.info("Subido por PAR a %s", objeto)
                    return True
        except urllib.error.URLError as e:
            log.error("Fallo la subida por PAR: %s", e)

    log.warning("OCI no configurado: %s no se publico.", nombre_objeto)
    return False


# --------------------------------------------------------------- descarga

def descargar(nombre_objeto: str, ruta_destino: str) -> bool:
    """Descarga un objeto a una ruta local. True si quedo en disco.

    Escribe en un temporal y renombra al final, para que una descarga
    interrumpida no deje un .joblib truncado.
    """
    objeto = _ruta_objeto(nombre_objeto)
    os.makedirs(os.path.dirname(os.path.abspath(ruta_destino)), exist_ok=True)
    temporal = ruta_destino + ".parcial"

    cliente = _cliente_sdk()
    if cliente and _bucket() and _namespace():
        try:
            respuesta = cliente.get_object(_namespace(), _bucket(), objeto)
            with open(temporal, "wb") as f:
                for trozo in respuesta.data.raw.stream(1024 * 1024, decode_content=False):
                    f.write(trozo)
            os.replace(temporal, ruta_destino)
            log.info("Descargado %s", uri(nombre_objeto))
            return True
        except Exception as e:
            log.warning("Fallo la descarga por SDK (%s): %s", type(e).__name__, e)
            _limpiar(temporal)

    par = _par_url()
    if par:
        try:
            with urllib.request.urlopen(par + objeto, timeout=TIEMPO_ESPERA) as r, \
                    open(temporal, "wb") as f:
                while trozo := r.read(1024 * 1024):
                    f.write(trozo)
            os.replace(temporal, ruta_destino)
            log.info("Descargado por PAR: %s", objeto)
            return True
        except urllib.error.URLError as e:
            log.warning("Fallo la descarga por PAR: %s", e)
            _limpiar(temporal)

    return False


def _limpiar(ruta: str) -> None:
    try:
        if os.path.exists(ruta):
            os.remove(ruta)
    except OSError:
        pass
