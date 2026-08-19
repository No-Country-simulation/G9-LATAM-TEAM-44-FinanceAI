"""Pruebas de contrato del ml-service.

Se comprueba la forma de la respuesta y las invariantes que el backend da por
ciertas, no los valores del modelo: fijar `probabilidad == 0.90` romperia el
test en cada reentrenamiento sin que nada este mal.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
import features

CATEGORIAS_VALIDAS = set(features.CATEGORIAS)
PERFILES_VALIDOS = set(features.PERFILES)


@pytest.fixture(scope="module")
def cliente():
    # El context manager dispara el lifespan, que es donde se cargan los modelos.
    with TestClient(app) as c:
        yield c


# ------------------------------------------------------------ diagnostico
def test_health_responde_sin_depender_del_modelo(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_modelo_info_declara_su_procedencia(cliente):
    cuerpo = cliente.get("/modelo/info").json()
    assert cuerpo["origen"] in {"oci", "local", "reglas"}
    assert set(cuerpo["categorias"]) == CATEGORIAS_VALIDAS
    assert set(cuerpo["perfiles"]) == PERFILES_VALIDOS
    assert 0 <= cuerpo["umbral_confianza"] <= 1


# ------------------------------------------------------------ clasificar
def test_clasificar_devuelve_una_categoria_por_transaccion(cliente):
    entrada = [
        {"descripcion": "Supermercado Exito", "valor": 420},
        {"descripcion": "Gasolinera Terpel", "valor": 300},
        {"descripcion": "Netflix Streaming", "valor": 40},
        {"descripcion": "Farmacia San Pablo", "valor": 80},
    ]
    r = cliente.post("/clasificar", json={"transacciones": entrada})
    assert r.status_code == 200

    clasificadas = r.json()["transacciones_clasificadas"]
    # El backend empareja por indice, asi que el orden y el numero importan.
    assert len(clasificadas) == len(entrada)
    assert [t["descripcion"] for t in clasificadas] == [t["descripcion"] for t in entrada]

    for t in clasificadas:
        assert t["categoria"] in CATEGORIAS_VALIDAS
        assert 0 <= t["confianza"] <= 1
        assert t["origen"] in {"modelo", "reglas"}


def test_clasificar_acierta_los_comercios_evidentes(cliente):
    casos = {
        "Supermercado Exito": "alimentacion",
        "Gasolinera Terpel": "transporte",
        "Farmacia San Pablo": "salud",
        "Arriendo Apartamento": "vivienda",
        "Netflix Streaming": "ocio",
    }
    r = cliente.post("/clasificar", json={
        "transacciones": [{"descripcion": d, "valor": 100} for d in casos]
    })
    obtenidas = {t["descripcion"]: t["categoria"] for t in r.json()["transacciones_clasificadas"]}
    assert obtenidas == casos


def test_clasificar_resiste_descripciones_sucias(cliente):
    """Las descripciones del banco llegan con ruido."""
    r = cliente.post("/clasificar", json={"transacciones": [
        {"descripcion": "TRF/POS Supermercado Jumbo REF993021 BOGOTA", "valor": 200},
        {"descripcion": "### farmacia cruz verde", "valor": 50},
    ]})
    categorias = [t["categoria"] for t in r.json()["transacciones_clasificadas"]]
    assert categorias == ["alimentacion", "salud"]


def test_clasificar_degrada_a_otras_lo_que_no_reconoce(cliente):
    r = cliente.post("/clasificar", json={
        "transacciones": [{"descripcion": "zxqw plfj mmnb", "valor": 10}]
    })
    assert r.json()["transacciones_clasificadas"][0]["categoria"] == "otras"


def test_el_resumen_agrega_sin_perder_ni_duplicar(cliente):
    entrada = [
        {"descripcion": "Supermercado Exito", "valor": 420},
        {"descripcion": "Uber Trip", "valor": 300},
        {"descripcion": "Supermercado Jumbo", "valor": 80},
    ]
    resumen = cliente.post("/clasificar", json={"transacciones": entrada}).json()["resumen_gastos"]

    # Solo categorias con gasto, y todas canonicas.
    assert set(resumen) <= CATEGORIAS_VALIDAS
    assert all(v > 0 for v in resumen.values())
    assert resumen["alimentacion"] == pytest.approx(500)  # 420 + 80
    assert sum(resumen.values()) == pytest.approx(sum(t["valor"] for t in entrada))


@pytest.mark.parametrize("cuerpo", [
    {"transacciones": []},
    {"transacciones": [{"descripcion": "", "valor": 10}]},
    {"transacciones": [{"descripcion": "Compra", "valor": 0}]},
    {"transacciones": [{"descripcion": "Compra", "valor": -5}]},
    {"transacciones": [{"descripcion": "x" * 201, "valor": 10}]},
    {},
])
def test_clasificar_rechaza_entradas_invalidas(cliente, cuerpo):
    assert cliente.post("/clasificar", json=cuerpo).status_code == 422


# ---------------------------------------------------------------- perfil
def test_perfil_respeta_el_contrato(cliente):
    r = cliente.post("/perfil", json={
        "ingreso_mensual": 4500, "nivel_endeudamiento": 25, "frecuencia_ahorro": "Media",
        "resumen_gastos": {"alimentacion": 420, "transporte": 300, "ocio": 40},
    })
    assert r.status_code == 200

    cuerpo = r.json()
    assert cuerpo["perfil_financiero"] in PERFILES_VALIDOS
    assert 0 <= cuerpo["probabilidad"] <= 1
    assert len(cuerpo["factores"]) == 3
    for factor in cuerpo["factores"]:
        assert factor["impacto"] in {"sube_riesgo", "baja_riesgo"}
        assert isinstance(factor["valor"], (int, float))


def test_perfil_distingue_una_situacion_sana_de_una_critica(cliente):
    """Quien gasta mas de lo que ingresa y esta muy endeudado no puede salir
    'Saludable', prediga lo que prediga el modelo."""
    sano = cliente.post("/perfil", json={
        "ingreso_mensual": 5000, "nivel_endeudamiento": 5, "frecuencia_ahorro": "Alta",
        "resumen_gastos": {"alimentacion": 400, "vivienda": 800},
    }).json()

    critico = cliente.post("/perfil", json={
        "ingreso_mensual": 1500, "nivel_endeudamiento": 80, "frecuencia_ahorro": "Nula",
        "resumen_gastos": {"alimentacion": 900, "ocio": 800, "vivienda": 1200},
    }).json()

    assert sano["perfil_financiero"] == "Saludable"
    assert critico["perfil_financiero"] == "En riesgo"
    assert critico["probabilidad"] >= 0.5


@pytest.mark.parametrize("frecuencia", ["Alta", "media", "BAJA", "nula"])
def test_perfil_acepta_la_frecuencia_en_cualquier_capitalizacion(cliente, frecuencia):
    r = cliente.post("/perfil", json={
        "ingreso_mensual": 3000, "nivel_endeudamiento": 20,
        "frecuencia_ahorro": frecuencia, "resumen_gastos": {"ocio": 100},
    })
    assert r.status_code == 200


@pytest.mark.parametrize("cuerpo", [
    {"ingreso_mensual": 4500, "nivel_endeudamiento": 25, "frecuencia_ahorro": "Siempre",
     "resumen_gastos": {"ocio": 10}},
    {"ingreso_mensual": 0, "nivel_endeudamiento": 25, "frecuencia_ahorro": "Media",
     "resumen_gastos": {"ocio": 10}},
    {"ingreso_mensual": 4500, "nivel_endeudamiento": 120, "frecuencia_ahorro": "Media",
     "resumen_gastos": {"ocio": 10}},
    {"ingreso_mensual": 4500, "nivel_endeudamiento": -1, "frecuencia_ahorro": "Media",
     "resumen_gastos": {"ocio": 10}},
])
def test_perfil_rechaza_entradas_invalidas(cliente, cuerpo):
    assert cliente.post("/perfil", json=cuerpo).status_code == 422


def test_perfil_ignora_categorias_desconocidas_sin_romperse(cliente):
    """Un cliente viejo puede mandar una categoria que ya no existe."""
    r = cliente.post("/perfil", json={
        "ingreso_mensual": 3000, "nivel_endeudamiento": 20, "frecuencia_ahorro": "Media",
        "resumen_gastos": {"alimentacion": 300, "entretenimiento": 100},
    })
    assert r.status_code == 200
