"""Pruebas de GET /modelo/metricas (Fase 16).

El endpoint es un espejo del contenido de
ciencia-datos/artefactos/metricas_resumen.json (generado por
generar_resumen_metricas.py), asi que aqui solo se verifica la forma de la
respuesta, no los valores exactos del modelo actual.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modelos import registro


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


def test_modelo_metricas_responde_200_cuando_el_artefacto_existe(cliente):
    if registro.metricas_resumen() is None:
        pytest.skip("metricas_resumen.json no esta disponible en este entorno")

    r = cliente.get("/modelo/metricas")
    assert r.status_code == 200

    cuerpo = r.json()
    for clave in (
        "version_modelo", "fecha", "baseline", "cv_agrupada",
        "matriz_confusion", "metricas_por_categoria", "calibracion", "benchmark",
    ):
        assert clave in cuerpo


def test_modelo_metricas_trae_las_8_categorias(cliente):
    if registro.metricas_resumen() is None:
        pytest.skip("metricas_resumen.json no esta disponible en este entorno")

    cuerpo = cliente.get("/modelo/metricas").json()
    assert len(cuerpo["metricas_por_categoria"]) == 8
    assert len(cuerpo["matriz_confusion"]["categorias"]) == 8
    assert len(cuerpo["matriz_confusion"]["matriz"]) == 8
    assert all(len(fila) == 8 for fila in cuerpo["matriz_confusion"]["matriz"])


def test_modelo_metricas_trae_baseline_particion_aleatoria_y_comercio_no_visto(cliente):
    if registro.metricas_resumen() is None:
        pytest.skip("metricas_resumen.json no esta disponible en este entorno")

    baseline = cliente.get("/modelo/metricas").json()["baseline"]
    for particion in ("particion_aleatoria", "comercio_no_visto"):
        assert 0 <= baseline[particion]["accuracy"] <= 1
        assert 0 <= baseline[particion]["f1_macro"] <= 1


def test_modelo_metricas_404_cuando_no_hay_artefacto(cliente, monkeypatch):
    monkeypatch.setattr(registro, "metricas_resumen", lambda: None)
    r = cliente.get("/modelo/metricas")
    assert r.status_code == 404
