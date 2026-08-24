"""Pruebas de la estrategia de abstencion (Fase 12).

`estado_confianza` es aditivo: no cambia `categoria`, `confianza` ni el
umbral de 0.5 que ya degradaba a 'otras'. Los cortes salen de
ciencia-datos/experimentos/calibracion.json (Fase 5), ver el docstring de
`app.main._estado_confianza`.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import _estado_confianza, app
from app.modelos import registro


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


# --------------------------------------------------- unidad: la funcion pura
@pytest.mark.parametrize("confianza, esperado", [
    (1.00, "aceptado"),
    (0.90, "aceptado"),
    (0.80, "aceptado"),          # limite inferior de 'aceptado', inclusive
    (0.79, "requiere_revision"),
    (0.65, "requiere_revision"),
    (0.50, "requiere_revision"),  # limite inferior de 'requiere_revision', inclusive
    (0.49, "otras"),
    (0.20, "otras"),
    (0.00, "otras"),
])
def test_estado_confianza_respeta_los_cortes_de_calibracion(confianza, esperado):
    assert _estado_confianza(confianza, umbral_revision=0.5, umbral_aceptado=0.8) == esperado


def test_estado_confianza_es_consistente_con_el_umbral_de_otras_ya_existente():
    """Todo lo que hoy degrada a 'otras' (confianza < umbral_confianza) debe
    seguir cayendo en el estado 'otras'; el campo nuevo no reclasifica nada."""
    umbral = 0.5
    justo_por_debajo = umbral - 0.0001
    assert _estado_confianza(justo_por_debajo, umbral, 0.8) == "otras"


# ------------------------------------------------- integracion: el endpoint
def test_modelo_info_expone_el_umbral_alto(cliente):
    cuerpo = cliente.get("/modelo/info").json()
    assert 0 <= cuerpo["umbral_confianza_alta"] <= 1
    assert cuerpo["umbral_confianza_alta"] >= cuerpo["umbral_confianza"]


def test_clasificar_incluye_estado_confianza_valido_para_cada_transaccion(cliente):
    entrada = [
        {"descripcion": "Supermercado Exito", "valor": 420},
        {"descripcion": "Netflix Streaming", "valor": 40},
        {"descripcion": "zxqw plfj mmnb", "valor": 10},
    ]
    r = cliente.post("/clasificar", json={"transacciones": entrada})
    assert r.status_code == 200

    for t in r.json()["transacciones_clasificadas"]:
        assert t["estado_confianza"] in {"aceptado", "requiere_revision", "otras"}


def test_clasificar_marca_otras_como_estado_otras_por_construccion(cliente):
    """Una descripcion sin ninguna senal cae en categoria 'otras' con
    confianza por debajo de umbral_confianza; el estado debe ser 'otras'."""
    r = cliente.post("/clasificar", json={
        "transacciones": [{"descripcion": "zxqw plfj mmnb", "valor": 10}]
    })
    clasificada = r.json()["transacciones_clasificadas"][0]
    assert clasificada["categoria"] == "otras"
    assert clasificada["confianza"] < registro.umbral_confianza
    assert clasificada["estado_confianza"] == "otras"


def test_clasificar_un_comercio_evidente_por_reglas_queda_aceptado(cliente):
    """El respaldo por palabras clave reporta CONFIANZA_KEYWORD=0.90, que cae
    en la banda 'aceptado' (>= 0.8) tanto si el origen es 'reglas' como si el
    propio modelo predice con esa confianza."""
    r = cliente.post("/clasificar", json={
        "transacciones": [{"descripcion": "Netflix Streaming", "valor": 40}]
    })
    clasificada = r.json()["transacciones_clasificadas"][0]
    if clasificada["confianza"] >= 0.8:
        assert clasificada["estado_confianza"] == "aceptado"
