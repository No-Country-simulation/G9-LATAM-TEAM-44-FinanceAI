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
    assert vector["tasa_gasto"] == 0
    assert all(math.isfinite(v) for v in vector.values())


def test_la_concentracion_distingue_gasto_repartido_de_gasto_unico():
    concentrado = features.construir_features_perfil(3000, 0, "Alta", {"vivienda": 1000})
    repartido = features.construir_features_perfil(
        3000, 0, "Alta", {c: 125 for c in features.CATEGORIAS})

    # Herfindahl: 1 con todo en una categoria, 1/N repartido entre las N.
    assert concentrado["concentracion_gasto"] == pytest.approx(1.0)
    assert repartido["concentracion_gasto"] == pytest.approx(1 / len(features.CATEGORIAS))


def test_el_vector_no_contiene_montos():
    """Ninguna columna puede ser un monto.

    La aplicacion acepta varias monedas y no las convierte, asi que un monto en
    el vector hace que el diagnostico dependa de la unidad en la que el usuario
    escriba las cifras.
    """
    vector = features.construir_features_perfil(
        3000, 25, "Media", {"alimentacion": 500, "vivienda": 900})

    # Un ratio, un porcentaje o un conteo no pueden acercarse a la escala del
    # ingreso ni del gasto. Cualquier columna que lo haga es un monto colado.
    assert all(abs(v) <= 100 for v in vector.values())


@pytest.mark.parametrize("factor", [20, 350, 1000, 4000])
def test_el_vector_es_invariante_a_la_moneda(factor):
    """Misma situacion economica, distinta unidad, mismo vector.

    Es la regresion del fallo que daba diagnosticos distintos al cambiar de
    dolares a pesos: los montos crudos salian del rango de entrenamiento y el
    escalador los mandaba a z-scores enormes.
    """
    gastos = {"vivienda": 900, "alimentacion": 500, "transporte": 400}
    base = features.construir_features_perfil(3000, 20, "Media", gastos)
    escalado = features.construir_features_perfil(
        3000 * factor, 20, "Media", {c: v * factor for c, v in gastos.items()})

    for columna in features.COLUMNAS_PERFIL:
        assert escalado[columna] == pytest.approx(base[columna]), columna


def test_los_pagos_de_deuda_van_a_su_categoria():
    """Una tarjeta o una cuota no son un gasto de consumo mas.

    Antes caian en "otras" porque el normalizador borraba "credito" junto con
    los prefijos de extracto, y la descripcion se quedaba en "tarjeta de".
    """
    from app.reglas import clasificar_por_reglas

    for descripcion in ("PAGO TARJETA DE CREDITO", "Pago Minimo Tarjeta Visa",
                        "ABONO TARJETA MASTERCARD", "CUOTA PRESTAMO BANCARIO",
                        "Avance Tarjeta de Credito", "Cuota de Manejo Tarjeta"):
        categoria, _ = clasificar_por_reglas(descripcion)
        assert categoria == "deudas", descripcion


def test_lo_que_lleva_tarjeta_o_credito_sin_ser_deuda_no_se_confunde():
    """Los dos casos que se rozan con la categoria nueva."""
    from app.reglas import clasificar_por_reglas

    assert clasificar_por_reglas("Recarga Tarjeta Metro")[0] == "transporte"
    assert clasificar_por_reglas("Credito Hipotecario")[0] == "vivienda"


def test_agregar_por_categoria_devuelve_todas_las_categorias():
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
