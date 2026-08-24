"""Pruebas del campo `top3` en /clasificar (Fase 16).

`top3` es aditivo: no cambia `categoria`, `confianza`, `origen` ni
`estado_confianza` (Fase 12). Se comprueban las invariantes generales -- orden
descendente, longitud <=3, la categoria principal siempre de primera -- no
valores fijos de probabilidad, que cambiarian con cada reentrenamiento sin que
nada este mal (mismo criterio que test_contrato.py).
"""
import features
import pytest
from fastapi.testclient import TestClient

from app.main import _top3_desde_fila, app

CATEGORIAS_VALIDAS = set(features.CATEGORIAS)


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


def _clasificar(cliente, descripcion: str, valor: float = 100) -> dict:
    r = cliente.post("/clasificar", json={
        "transacciones": [{"descripcion": descripcion, "valor": valor}]
    })
    assert r.status_code == 200
    return r.json()["transacciones_clasificadas"][0]


# --------------------------------------------------- unidad: la funcion pura
def test_top3_desde_fila_respeta_el_orden_descendente():
    clases = list(features.CATEGORIAS)
    fila = [0.05] * len(clases)
    fila[clases.index("alimentacion")] = 0.7
    fila[clases.index("transporte")] = 0.2
    fila[clases.index("salud")] = 0.1

    top3 = _top3_desde_fila(fila, clases, "alimentacion", 0.7)

    assert len(top3) == 3
    probabilidades = [p for _, p in top3]
    assert probabilidades == sorted(probabilidades, reverse=True)


def test_top3_desde_fila_pone_siempre_primera_la_categoria_principal():
    """Incluso si la categoria principal no es la de mayor probabilidad cruda
    (por ejemplo, cuando el umbral la degrado a 'otras'), debe quedar de
    primera: es la decision final, no la lectura cruda del modelo."""
    clases = list(features.CATEGORIAS)
    fila = [0.05] * len(clases)
    fila[clases.index("alimentacion")] = 0.6  # la mas probable segun el modelo
    fila[clases.index("otras")] = 0.1

    top3 = _top3_desde_fila(fila, clases, "otras", 0.1)

    assert top3[0] == ("otras", 0.1)


def test_top3_desde_fila_no_duplica_categorias():
    clases = list(features.CATEGORIAS)
    fila = [1.0 / len(clases)] * len(clases)

    top3 = _top3_desde_fila(fila, clases, clases[0], fila[0])

    categorias = [c for c, _ in top3]
    assert len(categorias) == len(set(categorias))


def test_top3_desde_fila_respeta_el_limite():
    clases = list(features.CATEGORIAS)
    fila = [1.0 / len(clases)] * len(clases)

    top3 = _top3_desde_fila(fila, clases, clases[0], fila[0], limite=2)

    assert len(top3) == 2


# ------------------------------------------------- integracion: el endpoint
def test_clasificar_incluye_top3_con_longitud_valida(cliente):
    entrada = [
        {"descripcion": "Supermercado Exito", "valor": 420},
        {"descripcion": "Netflix Streaming", "valor": 40},
        {"descripcion": "zxqw plfj mmnb", "valor": 10},
    ]
    r = cliente.post("/clasificar", json={"transacciones": entrada})
    assert r.status_code == 200

    for t in r.json()["transacciones_clasificadas"]:
        assert 1 <= len(t["top3"]) <= 3
        for entrada_top in t["top3"]:
            assert entrada_top["categoria"] in CATEGORIAS_VALIDAS
            assert 0 <= entrada_top["confianza"] <= 1


def test_top3_esta_ordenado_de_forma_descendente(cliente):
    clasificada = _clasificar(cliente, "Supermercado Exito")
    confianzas = [c["confianza"] for c in clasificada["top3"]]
    assert confianzas == sorted(confianzas, reverse=True)


def test_top3_incluye_la_categoria_principal_como_primer_elemento(cliente):
    clasificada = _clasificar(cliente, "Supermercado Exito")
    assert clasificada["top3"][0]["categoria"] == clasificada["categoria"]
    assert clasificada["top3"][0]["confianza"] == clasificada["confianza"]


def test_top3_de_un_comercio_evidente_por_reglas_tiene_un_solo_elemento(cliente):
    """CONFIANZA_KEYWORD (0.90) cae por encima del umbral tipico, asi que el
    origen puede ser 'modelo' o 'reglas' segun lo entrenado; cuando el origen
    es 'reglas' (Fase 16), top3 trae un unico elemento porque no hay
    distribucion de probabilidades que ofrecer."""
    clasificada = _clasificar(cliente, "Netflix Streaming")
    if clasificada["origen"] == "reglas":
        assert len(clasificada["top3"]) == 1
        assert clasificada["top3"][0]["categoria"] == clasificada["categoria"]


def test_top3_sin_modelo_cargado_tiene_un_solo_elemento(cliente, monkeypatch):
    """Modo reglas globalmente (sin clasificador cargado): top3 siempre viene
    con un unico elemento, el de la propia regla."""
    from app.modelos import registro

    monkeypatch.setattr(registro, "clasificador", None)

    clasificada = _clasificar(cliente, "Supermercado Exito")

    assert clasificada["origen"] == "reglas"
    assert len(clasificada["top3"]) == 1
    assert clasificada["top3"][0]["categoria"] == clasificada["categoria"]
    assert clasificada["top3"][0]["confianza"] == clasificada["confianza"]
