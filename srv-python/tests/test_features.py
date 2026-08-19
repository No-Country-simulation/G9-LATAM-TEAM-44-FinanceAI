"""Pruebas de features.py, el modulo que comparten notebook y servicio.

Si esta transformacion cambia sin reentrenar, el modelo recibe vectores
distintos a los del entrenamiento y falla sin dar error. Estas pruebas fijan el
comportamiento para que el cambio no pase inadvertido.
"""
import math

import pytest

import features


# ---------------------------------------------------------- normalizacion
@pytest.mark.parametrize("entrada, esperado", [
    ("Supermercado Exito", "supermercado exito"),
    ("FARMACIA SAN PABLO", "farmacia san pablo"),
    ("Farmacía Guadalajara", "farmacia guadalajara"),
    ("### supermercado ara", "supermercado ara"),
    ("TRF/POS Cinepolis Entradas", "cinepolis entradas"),
])
def test_normalizar_texto_limpia_ruido_y_tildes(entrada, esperado):
    assert features.normalizar_texto(entrada) == esperado


def test_normalizar_texto_colapsa_referencias_numericas():
    """Sin el colapso, cada referencia seria un termino propio del vocabulario."""
    a = features.normalizar_texto("Supermercado Exito REF483920")
    b = features.normalizar_texto("Supermercado Exito REF119277")
    assert a == b
    assert "<num>" in a


@pytest.mark.parametrize("nulo", [None, "", "   ", float("nan"), "nan", "<NA>", "NaT"])
def test_normalizar_texto_trata_los_nulos_como_vacio(nulo):
    """Los nulos de pandas sobreviven a str() y acabarian como el token 'na'."""
    assert features.normalizar_texto(nulo) == ""


@pytest.mark.parametrize("entrada, esperado", [
    ("En observacion", "En observación"),
    ("EN OBSERVACIÓN", "En observación"),
    ("saludable", "Saludable"),
    ("En riesgo", "En riesgo"),
])
def test_normalizar_perfil_unifica_la_tilde(entrada, esperado):
    assert features.normalizar_perfil(entrada) == esperado


def test_normalizar_perfil_rechaza_lo_desconocido():
    with pytest.raises(ValueError):
        features.normalizar_perfil("Excelente")


def test_normalizar_categoria_degrada_a_otras():
    assert features.normalizar_categoria("entretenimiento") == "otras"
    assert features.normalizar_categoria(None) == "otras"
    assert features.normalizar_categoria("Alimentación") == "alimentacion"


# -------------------------------------------------------------- features
def test_el_vector_respeta_el_orden_contractual():
    vector = features.construir_features_perfil(
        3000, 25, "Media", {"alimentacion": 500, "vivienda": 900})
    assert list(vector) == list(features.COLUMNAS_PERFIL)
    assert len(vector) == len(features.COLUMNAS_PERFIL)


def test_las_tasas_se_calculan_como_toca():
    vector = features.construir_features_perfil(
        2000, 40, "Baja", {"alimentacion": 500, "vivienda": 500})

    assert vector["gasto_total"] == pytest.approx(1000)
    assert vector["tasa_gasto"] == pytest.approx(0.5)
    assert vector["capacidad_ahorro"] == pytest.approx(0.5)
    assert vector["ratio_endeudamiento"] == pytest.approx(0.4)
    assert vector["ahorro_ordinal"] == 1
    assert vector["pct_alimentacion"] == pytest.approx(0.5)
    assert vector["categorias_activas"] == 2


def test_la_capacidad_de_ahorro_puede_ser_negativa():
    """Gastar mas de lo que se ingresa es lo que separa 'En riesgo'; recortar a
    cero borraria esa senal."""
    vector = features.construir_features_perfil(1000, 10, "Nula", {"vivienda": 1500})
    assert vector["tasa_gasto"] == pytest.approx(1.5)
    assert vector["capacidad_ahorro"] == pytest.approx(-0.5)


def test_sin_gastos_no_hay_division_por_cero():
    vector = features.construir_features_perfil(3000, 0, "Alta", {})
    assert vector["gasto_total"] == 0
    assert vector["tasa_gasto"] == 0
    assert all(math.isfinite(v) for v in vector.values())


def test_la_concentracion_distingue_gasto_repartido_de_gasto_unico():
    concentrado = features.construir_features_perfil(3000, 0, "Alta", {"vivienda": 1000})
    repartido = features.construir_features_perfil(
        3000, 0, "Alta", {c: 125 for c in features.CATEGORIAS})

    assert concentrado["concentracion_gasto"] == pytest.approx(1.0)
    assert repartido["concentracion_gasto"] == pytest.approx(0.125)


def test_agregar_por_categoria_devuelve_siempre_las_ocho():
    resumen = features.agregar_por_categoria([
        {"categoria": "ocio", "monto": 40},
        {"categoria": "ocio", "monto": 60},
        {"categoria": "desconocida", "monto": 10},
        {"categoria": "alimentacion", "monto": -25},  # el signo no debe restar
    ])
    assert set(resumen) == set(features.CATEGORIAS)
    assert resumen["ocio"] == 100
    assert resumen["otras"] == 10
    assert resumen["alimentacion"] == 25


def test_vector_perfil_coincide_con_el_diccionario():
    argumentos = (4500, 25, "Media", {"alimentacion": 420, "transporte": 300})
    diccionario = features.construir_features_perfil(*argumentos)
    lista = features.vector_perfil(*argumentos)
    assert lista == [diccionario[c] for c in features.COLUMNAS_PERFIL]
