from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)

def test_clasificar_contrato():
    r = c.post("/clasificar", json={"transacciones": [
        {"descripcion": "Supermercado", "valor": 420},
        {"descripcion": "Combustible", "valor": 300},
        {"descripcion": "Netflix", "valor": 40},
        {"descripcion": "XYZ desconocido", "valor": 10},
    ]})
    assert r.status_code == 200
    tx = r.json()["transacciones_clasificadas"]
    assert [t["categoria"] for t in tx] == ["alimentacion", "transporte", "ocio", "otras"]
    assert all(0 <= t["confianza"] <= 1 for t in tx)

def test_perfil_contrato_espeja_umbral_java():
    r = c.post("/perfil", json={
        "ingreso_mensual": 4500, "nivel_endeudamiento": 25,
        "frecuencia_ahorro": "Media",
        "resumen_gastos": {"alimentacion": 420, "transporte": 300, "ocio": 40},
    })
    assert r.status_code == 200
    body = r.json()
    assert body["perfil_financiero"] == "Saludable"   # deuda<30 y ratio<0.8
    assert body["probabilidad"] == 0.90
    assert len(body["factores"]) == 3

def test_perfil_valida_frecuencia():
    r = c.post("/perfil", json={
        "ingreso_mensual": 4500, "nivel_endeudamiento": 25,
        "frecuencia_ahorro": "Siempre", "resumen_gastos": {"ocio": 10},
    })
    assert r.status_code == 422
