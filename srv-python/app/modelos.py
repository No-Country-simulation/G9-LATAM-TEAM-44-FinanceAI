"""Carga de los artefactos de modelo.

Se resuelven en este orden:

  1. OCI Object Storage. Es lo que se usa en despliegue: la imagen no lleva
     modelos dentro, los baja al arrancar.
  2. Disco local (ciencia-datos/artefactos/), lo que deja el notebook.
  3. Reglas por palabras clave, si no hay artefactos.

Nunca lanza por falta de modelo. Arrancar con capacidades reducidas y
declararlo en /modelo/info es mejor que no arrancar.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

# features.py y oci_storage.py: en la imagen Docker van dentro de app/, en
# local estan en ciencia-datos/.
_AQUI = Path(__file__).resolve().parent
for _candidata in (_AQUI / "ciencia_datos", _AQUI.parent.parent / "ciencia-datos"):
    if (_candidata / "features.py").exists():
        sys.path.insert(0, str(_candidata))
        break

import features  # noqa: E402
import oci_storage  # noqa: E402

NOMBRE_CLASIFICADOR = "clasificador_gastos.joblib"
NOMBRE_PERFIL = "modelo_perfil.joblib"
NOMBRE_METADATOS = "metadatos.json"
NOMBRE_METRICAS_RESUMEN = "metricas_resumen.json"

#: Donde aterrizan los artefactos descargados de OCI.
DIRECTORIO_ARTEFACTOS = Path(
    os.getenv("RUTA_ARTEFACTOS", str(_AQUI.parent / "artefactos"))
).resolve()

#: Rutas locales alternativas.
_RUTAS_LOCALES = [
    DIRECTORIO_ARTEFACTOS,
    _AQUI / "ciencia_datos" / "artefactos",
    _AQUI.parent.parent / "ciencia-datos" / "artefactos",
]


class RegistroModelos:
    """Contiene los modelos cargados y de dónde salieron."""

    def __init__(self) -> None:
        self.clasificador: Optional[Any] = None
        self.perfil: Optional[Any] = None
        self.metadatos: dict = {}
        self.origen: str = "sin_cargar"
        self.errores: list[str] = []

    # ------------------------------------------------------------- estado
    @property
    def version(self) -> str:
        return self.metadatos.get("version", "reglas-0.1")

    @property
    def umbral_confianza(self) -> float:
        return float(self.metadatos.get("umbral_confianza", 0.5))

    @property
    def umbral_confianza_alta(self) -> float:
        """Corte para el estado 'aceptado' (Fase 12, estrategia de abstencion).

        Tomado de ciencia-datos/experimentos/calibracion.json
        (coverage_vs_accuracy, Fase 5): en umbral=0.8 la accuracy de las
        predicciones aceptadas es 0.5223254795206358 (31959/58894 filas,
        coverage=0.5426529018236154) frente a un accuracy_global_ood de
        0.4264271402859374 -- +9.59 puntos absolutos (+22.5% relativo). Ver
        docs/API-ENDPOINTS.md para la tabla completa y la justificacion de
        por que no se usa 0.9 (coverage cae a 0.46) ni un valor menor a 0.8
        (la mejora sobre el promedio se diluye).
        """
        return float(self.metadatos.get("umbral_confianza_alta", 0.8))

    @property
    def referencia_saludable(self) -> dict:
        return self.metadatos.get("referencia_saludable", {})

    def columnas_validas(self) -> bool:
        """El orden de columnas del artefacto debe coincidir con features.py.

        Si no coincide, el modelo recibe los valores en posiciones distintas a
        las del entrenamiento y predice cualquier cosa sin dar error.
        """
        columnas = self.metadatos.get("columnas_perfil")
        return columnas is None or list(columnas) == list(features.COLUMNAS_PERFIL)

    def info(self) -> dict:
        return {
            "version": self.version,
            "origen": self.origen,
            "clasificador_cargado": self.clasificador is not None,
            "perfil_cargado": self.perfil is not None,
            "umbral_confianza": self.umbral_confianza,
            "umbral_confianza_alta": self.umbral_confianza_alta,
            "categorias": list(features.CATEGORIAS),
            "perfiles": list(features.PERFILES),
            "metricas": self.metadatos.get("metricas", {}),
            "entrenado_en": self.metadatos.get("entrenado_en"),
            "oci": oci_storage.describir(),
            "uri_esperada": oci_storage.uri(NOMBRE_CLASIFICADOR),
            "errores": self.errores,
        }

    # ------------------------------------------------------------- carga
    def cargar(self) -> None:
        self.errores = []
        directorio = self._resolver_directorio()
        if directorio is None:
            self.origen = "reglas"
            log.warning("Sin artefactos disponibles: el servicio opera con reglas por palabras clave.")
            return

        try:
            import joblib
        except ImportError:
            self.errores.append("joblib no instalado")
            self.origen = "reglas"
            return

        try:
            ruta_meta = directorio / NOMBRE_METADATOS
            if ruta_meta.exists():
                self.metadatos = json.loads(ruta_meta.read_text(encoding="utf-8"))

            if not self.columnas_validas():
                self.errores.append(
                    "columnas_perfil del artefacto no coinciden con features.COLUMNAS_PERFIL"
                )
                self.origen = "reglas"
                log.error("Artefacto incompatible con features.py; se ignora. %s", self.errores[-1])
                return

            self.clasificador = joblib.load(directorio / NOMBRE_CLASIFICADOR)
            self.perfil = joblib.load(directorio / NOMBRE_PERFIL)
            log.info("Modelos cargados desde %s (version %s)", directorio, self.version)
        except Exception as e:
            self.errores.append(f"{type(e).__name__}: {e}")
            self.clasificador = None
            self.perfil = None
            self.origen = "reglas"
            log.exception("No se pudieron cargar los modelos; se opera con reglas.")

    def metricas_resumen(self) -> Optional[dict]:
        """Contenido de ciencia-datos/artefactos/metricas_resumen.json (Fase 16),
        generado por ciencia-datos/scripts/generar_resumen_metricas.py.

        A diferencia del clasificador y el modelo de perfil, este archivo NO se
        descarga de OCI: viaja dentro de la imagen (ver Dockerfile, mismo COPY
        que los .joblib) o en el checkout local de ciencia-datos/. Por eso se
        busca directamente en las rutas locales, sin pasar por
        `_resolver_directorio`.
        """
        for ruta in _RUTAS_LOCALES:
            candidato = ruta / NOMBRE_METRICAS_RESUMEN
            if candidato.exists():
                try:
                    return json.loads(candidato.read_text(encoding="utf-8"))
                except Exception as e:
                    log.warning("metricas_resumen.json ilegible en %s: %s", candidato, e)
                    return None
        return None

    def _resolver_directorio(self) -> Optional[Path]:
        """OCI primero, luego las rutas locales."""
        if oci_storage.configurado():
            DIRECTORIO_ARTEFACTOS.mkdir(parents=True, exist_ok=True)
            descargados = all(
                oci_storage.descargar(nombre, str(DIRECTORIO_ARTEFACTOS / nombre))
                for nombre in (NOMBRE_CLASIFICADOR, NOMBRE_PERFIL, NOMBRE_METADATOS)
            )
            if descargados:
                self.origen = "oci"
                return DIRECTORIO_ARTEFACTOS
            self.errores.append("descarga desde OCI incompleta; se buscan artefactos locales")
            log.warning("OCI configurado pero la descarga fallo; se intenta con artefactos locales.")

        for ruta in _RUTAS_LOCALES:
            if (ruta / NOMBRE_CLASIFICADOR).exists() and (ruta / NOMBRE_PERFIL).exists():
                self.origen = "local"
                return ruta
        return None


#: La usan los endpoints.
registro = RegistroModelos()
