"""Generador del dataset financiero sintetico.

Produce extractos bancarios con ruido, mas las dos etiquetas que hacen falta:
`categoria` por transaccion (clasificador de gastos) y `perfil` por usuario
(modelo de salud financiera).

Se genera por simulacion porque no hay corpus publico en espanol de extractos
etiquetados por categoria. El notebook detalla que implica eso para las
metricas.

Salida (--salida, por defecto ciencia-datos/datos/crudos):
  usuario_XXX_<S|O|R>.{json,csv,xlsx}   un extracto por usuario, formato mixto
  usuarios.csv                          atributos y etiqueta por usuario

Uso:
    python ciencia-datos/scripts/generador_usuarios.py --usuarios 400 --semilla 42
"""
from __future__ import annotations

import argparse
import json
import os
import random
from datetime import datetime

import pandas as pd

# ----------------------------------------------------------------- catalogos
# Comercios de varios paises de LATAM. Con un catalogo corto el clasificador
# memoriza cadenas exactas y las metricas salen infladas.

CATALOGO_VARIABLE: dict[str, list[str]] = {
    "alimentacion": [
        "Supermercado Exito", "Almacenes Jumbo", "Walmart Express", "OXXO Tienda",
        "Tienda D1", "Ara Supermercado", "Carulla Express", "La Comer",
        "Soriana Hiper", "Supermercado Lider", "Coto Supermercado", "Dia Market",
        "Plaza Vea", "Tottus Market", "Panaderia La Espiga", "Fruteria El Huerto",
        "Carniceria Don Pepe", "McDonalds", "Burger King", "Rappi Comida",
        "Uber Eats Pedido", "PedidosYa", "Domicilios Restaurante", "Starbucks Cafe",
        "Juan Valdez Cafe", "Subway Sandwich", "Pizzeria Napoli", "Comida China Wok",
        "Mercado Central Puesto", "Minimarket La Esquina",
    ],
    "transporte": [
        "Gasolinera Primax", "Gasolinera Pemex", "Estacion Terpel", "Shell Combustible",
        "Petrobras Estacion", "YPF Servicio", "Copec Bencina", "Uber Trip",
        "DiDi Ride", "Cabify Viaje", "InDrive Viaje", "Taxi Amarillo",
        "Recarga Tarjeta Metro", "Transmilenio Recarga", "Subte Sube Carga",
        "Peaje Autopista", "Parqueadero Centro", "Taller Mecanico Luis",
        "Lavadero de Autos", "Repuestos Automotriz", "Llantas y Rines",
        "Pasaje Bus Intermunicipal", "Tecnomecanica Revision", "SOAT Seguro Vehiculo",
    ],
    "salud": [
        "Farmacia San Pablo", "Drogueria Cruz Verde", "Farmacia Guadalajara",
        "Farmacias Ahumada", "Farmacity Sucursal", "Inkafarma Botica",
        "Consulta Medica General", "Laboratorio Clinico Sur", "Clinica Dental Sonrisa",
        "Optica Vision Center", "Hospital Universitario", "Terapia Fisica Centro",
        "Examenes de Laboratorio", "Consulta Especialista", "Vacunacion Centro",
        "Medicamentos Recetados", "EPS Cuota Moderadora", "Psicologia Consulta",
    ],
    "vivienda": [
        "Arriendo Apartamento", "Alquiler Departamento", "Renta Mensual Casa",
        "Administracion Edificio", "Cuota Hipoteca Vivienda", "Seguro Hogar Anual",
        "Impuesto Predial", "Ferreteria El Martillo", "Homecenter Sodimac",
        "Easy Construccion", "Muebles para el Hogar", "Servicio Cerrajeria",
        "Reparacion Plomeria", "Pintura y Acabados", "Aseo y Limpieza Hogar",
    ],
    "educacion": [
        "Curso Udemy Online", "Suscripcion Platzi", "Coursera Certificado",
        "Libreria Panamericana", "Libreria Gandhi", "Matricula Universidad",
        "Pension Colegio", "Instituto de Idiomas", "Utiles Escolares",
        "Fotocopias Universitarias", "Examen de Certificacion", "Taller de Programacion",
    ],
    # El streaming va en ocio, no en servicios: es lo que hace el ejemplo del
    # reto y lo que responden las keywords del backend. Si no coincidieran, el
    # modo modelo y el degradado darian categorias distintas.
    "ocio": [
        "Cinepolis Entradas", "Cinemark Boleteria", "Cine Colombia", "Steam Games",
        "PlayStation Store", "Xbox Game Pass", "Bar El Callejon", "Cerveceria Artesanal",
        "Restaurante Gourmet", "Discoteca Nocturna", "Concierto Entradas",
        "Parque de Diversiones", "Gimnasio SmartFit", "Bowling Centro",
        "Museo Entrada", "Viaje Fin de Semana", "Hotel Reserva", "Escape Room",
        "Netflix Streaming", "Spotify Premium", "Disney Plus Suscripcion",
        "HBO Max Mensual", "Amazon Prime Video", "YouTube Premium",
    ],
    "servicios": [
        "Claro Telefonia Movil", "Movistar Internet Hogar", "Tigo Une Plan",
        "Entel Plan Movil", "WOM Recarga", "Personal Flow Internet",
        "Pago Luz Enel", "Servicio Agua Potable", "Gas Natural Domiciliario",
        "Energia Electrica EPM", "Recoleccion Basuras", "Almacenamiento iCloud",
        "Microsoft 365 Suscripcion", "Antivirus Licencia Anual",
    ],
    "otras": [
        "Retiro Cajero Automatico", "Transferencia a Terceros", "Comision Bancaria",
        "Cuota de Manejo Tarjeta", "Envio de Remesa", "Donacion Fundacion",
        "Regalo Cumpleanos", "Peluqueria y Barberia", "Lavanderia Express",
        "Tienda de Ropa Zara", "Zapateria Centro", "Perfumeria Belleza",
        "Veterinaria Mascota", "Alimento para Mascota", "Compra Marketplace",
        "Mercado Libre Compra", "AliExpress Pedido", "Amazon Compra",
        "Impuesto Retencion", "Seguro de Vida Cuota",
    ],
}

# Recurrentes: mismo comercio, mismo dia, todos los meses.
CATALOGO_FIJO_MENSUAL: dict[str, list[str]] = {
    "vivienda": ["Arriendo Apartamento", "Administracion Edificio", "Cuota Hipoteca Vivienda"],
    "servicios": [
        "Pago Luz Enel", "Servicio Agua Potable", "Gas Natural Domiciliario",
        "Claro Telefonia Movil", "Movistar Internet Hogar",
    ],
    "ocio": [
        "Gimnasio SmartFit", "Netflix Streaming", "Spotify Premium",
        "Disney Plus Suscripcion",
    ],
    "salud": ["EPS Cuota Moderadora"],
}

CATALOGO_ANUAL: dict[str, list[str]] = {
    "servicios": ["Renovacion Hosting Web", "Antivirus Licencia Anual"],
    "ocio": ["Amazon Prime Anual"],
    "vivienda": ["Seguro Hogar Anual", "Impuesto Predial"],
    "transporte": ["SOAT Seguro Vehiculo", "Tecnomecanica Revision"],
    "educacion": ["Matricula Universidad"],
}

CATALOGO_INGRESOS = [
    "PAGO NOMINA SUELDO", "TRANSFERENCIA DEPOSITO SALARIO", "ABONO NOMINA EMPRESA",
    "PAGO HONORARIOS FREELANCE", "DEPOSITO QUINCENA",
]

CATALOGO_DEUDAS = [
    "PAGO TARJETA DE CREDITO", "CUOTA PRESTAMO BANCARIO", "CREDITO HIPOTECARIO",
    "PAGO PRESTAMO AUTOMOTRIZ", "ABONO EXTRAORDINARIO HIPOTECA", "CUOTA CREDITO LIBRE INVERSION",
]

MAPEO_LETRAS = {"Saludable": "S", "En observación": "O", "En riesgo": "R"}
FORMATOS = ["json", "csv", "xlsx"]

CARACTERES_BASURA = ["#", "*", "$$", "%", "///", "---", "ERR:", "..", "**"]
CIUDADES = ["BOGOTA", "MEDELLIN", "CDMX", "LIMA", "SANTIAGO", "BUENOS AIRES", "QUITO", "CALI"]


# ------------------------------------------------------------------- ruido

def _typo(texto: str, rng: random.Random) -> str:
    """Error tipografico de una letra.

    Obliga al clasificador a apoyarse en n-gramas de caracteres en vez de
    memorizar la cadena exacta.
    """
    if len(texto) < 4:
        return texto
    i = rng.randrange(len(texto) - 1)
    modo = rng.random()
    if modo < 0.4:  # intercambio de letras contiguas
        return texto[:i] + texto[i + 1] + texto[i] + texto[i + 2:]
    if modo < 0.7:  # letra perdida
        return texto[:i] + texto[i + 1:]
    return texto[:i] + texto[i] + texto[i:]  # letra duplicada


def inyectar_ruido_texto(texto: str, rng: random.Random) -> str:
    """Ensucia la descripcion imitando un extracto bancario."""
    if rng.random() < 0.20:
        texto = texto.upper()
    elif rng.random() < 0.30:
        texto = texto.lower()

    if rng.random() < 0.12:
        texto = _typo(texto, rng)
    if rng.random() < 0.20:
        texto = f"{rng.choice(CARACTERES_BASURA)} {texto}"
    if rng.random() < 0.18:
        texto = f"TRF/POS {texto}"
    if rng.random() < 0.15:
        texto = f"{texto} {rng.choice(CIUDADES)}"
    if rng.random() < 0.15:
        texto = f"{texto} REF{rng.randrange(100000, 999999)}"
    if rng.random() < 0.08:
        texto = texto[: max(6, len(texto) - rng.randrange(1, 5))]  # truncado
    return texto


# ------------------------------------------------------------- etiquetado

def calcular_perfil(factor_gasto: float, nivel_endeudamiento: float,
                    ahorro_ordinal: int, rng: random.Random) -> tuple[str, float]:
    """Deriva la etiqueta de perfil de los rasgos latentes del usuario.

    Es la regla que el modelo tendra que reconstruir desde los agregados. El
    ruido gaussiano evita una frontera perfectamente separable.

    El gasto sobre ingreso pesa mas que la deuda, y el ahorro atenua. Misma
    intuicion que los umbrales de respaldo del backend.
    """
    presion_gasto = min(max((factor_gasto - 0.50) / 0.90, 0.0), 1.0)
    presion_deuda = min(max(nivel_endeudamiento / 85.0, 0.0), 1.0)
    falta_ahorro = 1.0 - (ahorro_ordinal / 3.0)

    score = 0.45 * presion_gasto + 0.35 * presion_deuda + 0.20 * falta_ahorro
    score_ruidoso = score + rng.gauss(0.0, 0.06)

    if score_ruidoso < 0.33:
        return "Saludable", score
    if score_ruidoso < 0.58:
        return "En observación", score
    return "En riesgo", score


def _sortear_ahorro(factor_gasto: float, rng: random.Random) -> str:
    """Quien gasta poco tiende a ahorrar mas seguido. Correlacion, no regla."""
    holgura = max(0.0, 1.2 - factor_gasto)
    pesos = [holgura ** 2, holgura, 0.6, 0.4]  # Alta, Media, Baja, Nula
    return rng.choices(["Alta", "Media", "Baja", "Nula"], weights=pesos, k=1)[0]


# ------------------------------------------------------------- generacion

def sumar_meses(fecha: datetime, n: int) -> datetime:
    """Avanza n meses calendario, siempre al dia 1.

    Sumar 30 dias desfasa y reparte un mismo mes entre dos naturales, con lo
    que los agregados mensuales salen sobre periodos incompletos.
    """
    total = (fecha.year * 12 + fecha.month - 1) + n
    return fecha.replace(year=total // 12, month=total % 12 + 1, day=1)


def generar_usuario(idx: int, meses: int, fecha_base: datetime,
                    rng: random.Random) -> tuple[dict, list[dict]]:
    """Genera los atributos y el extracto completo de un usuario."""
    ingreso_mensual = round(rng.uniform(1200, 7000), 2)
    factor_gasto = rng.uniform(0.45, 1.45)
    # La deuda correlaciona con el gasto pero conserva vida propia.
    nivel_endeudamiento = round(
        min(max(factor_gasto * 45 + rng.gauss(0, 14), 0.0), 85.0), 1
    )
    frecuencia_ahorro = _sortear_ahorro(factor_gasto, rng)
    ahorro_ordinal = {"Nula": 0, "Baja": 1, "Media": 2, "Alta": 3}[frecuencia_ahorro]

    perfil, score = calcular_perfil(factor_gasto, nivel_endeudamiento, ahorro_ordinal, rng)

    pagos_por_mes = rng.choice([1, 2])
    monto_por_pago = round(ingreso_mensual / pagos_por_mes, 2)
    dias_pago = [1] if pagos_por_mes == 1 else [1, 15]

    # Gastos recurrentes del usuario: se fijan una vez y se repiten cada mes.
    gastos_fijos = []
    for categoria, comercios in CATALOGO_FIJO_MENSUAL.items():
        for comercio in rng.sample(comercios, rng.randint(1, min(2, len(comercios)))):
            base = rng.uniform(180, 900) if categoria == "vivienda" else rng.uniform(12, 90)
            gastos_fijos.append({
                "descripcion": comercio,
                "categoria": categoria,
                "monto": round(base * (ingreso_mensual / 3500), 2),
                "dia": rng.randint(1, 28),
            })

    mes_anual = rng.randrange(meses)
    cat_anual = rng.choice(list(CATALOGO_ANUAL))
    desc_anual = rng.choice(CATALOGO_ANUAL[cat_anual])
    monto_anual = round(rng.uniform(90, 300), 2)

    transacciones: list[dict] = []

    for mes_idx in range(meses):
        mes = sumar_meses(fecha_base, mes_idx)
        acumulado = 0.0

        for dia in dias_pago:
            transacciones.append(_tx(
                mes.replace(day=dia), "ingresos",
                rng.choice(CATALOGO_INGRESOS), None, monto_por_pago, rng,
            ))

        for fijo in gastos_fijos:
            transacciones.append(_tx(
                mes.replace(day=fijo["dia"]), "egresos",
                fijo["descripcion"], fijo["categoria"], fijo["monto"], rng,
            ))
            acumulado += fijo["monto"]

        if mes_idx == mes_anual:
            transacciones.append(_tx(
                mes.replace(day=rng.randint(1, 28)), "egresos",
                desc_anual, cat_anual, monto_anual, rng,
            ))
            acumulado += monto_anual

        # El resto del presupuesto se reparte en gastos variables hasta llegar
        # al gasto objetivo del mes (ingreso * factor_gasto).
        objetivo = ingreso_mensual * factor_gasto
        presupuesto = max(0.0, objetivo - acumulado)
        cantidad = rng.randint(12, 28)
        if presupuesto > 0:
            promedio = presupuesto / cantidad
            for _ in range(cantidad):
                categoria = rng.choice(list(CATALOGO_VARIABLE))
                descripcion = rng.choice(CATALOGO_VARIABLE[categoria])
                monto = round(rng.uniform(promedio * 0.3, promedio * 1.8), 2)
                if rng.random() < 0.02:
                    monto = -monto  # signo invertido: lo corrige la limpieza
                transacciones.append(_tx(
                    mes.replace(day=rng.randint(1, 28)), "egresos",
                    descripcion, categoria, monto, rng,
                ))

        if rng.random() < 0.35:
            transacciones.append(_tx(
                mes.replace(day=rng.randint(1, 28)), "deudas",
                rng.choice(CATALOGO_DEUDAS), None,
                round(ingreso_mensual * nivel_endeudamiento / 100 * rng.uniform(0.2, 0.5), 2), rng,
            ))

    usuario = {
        "usuario_id": f"{idx:03d}",
        "ingreso_mensual": ingreso_mensual,
        "nivel_endeudamiento": nivel_endeudamiento,
        "frecuencia_ahorro": frecuencia_ahorro,
        "factor_gasto_latente": round(factor_gasto, 4),
        "score_riesgo_latente": round(score, 4),
        "perfil": perfil,
    }
    return usuario, transacciones


def _tx(fecha: datetime, tipo: str, descripcion: str, categoria: str | None,
        monto: float, rng: random.Random) -> dict:
    """Arma una transaccion ya ensuciada (fecha, descripcion y nulos)."""
    prob = rng.random()
    if prob < 0.15:
        fecha_str = fecha.strftime("%d/%m/%Y")
    elif prob < 0.19:
        fecha_str = None
    elif prob < 0.23:
        fecha_str = fecha.strftime("%Y/%m/%d")
    else:
        fecha_str = fecha.strftime("%Y-%m-%d")

    desc = None if rng.random() < 0.03 else inyectar_ruido_texto(descripcion, rng)

    return {
        "fecha": fecha_str,
        "tipo": tipo,
        "descripcion": desc,
        "monto": monto,
        # La etiqueta va limpia aunque la descripcion no lo este.
        "categoria": categoria,
        # Nombre del comercio antes de ensuciarlo. No existe en un extracto
        # real y el modelo no lo usa: sirve para particionar el experimento por
        # comercio en el notebook.
        "comercio": descripcion,
    }


def guardar(transacciones: list[dict], ruta_base: str, formato: str) -> str:
    columnas = ["fecha", "tipo", "descripcion", "monto", "categoria", "comercio"]
    ruta = f"{ruta_base}.{formato}"

    if formato == "json":
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(transacciones, f, ensure_ascii=False, indent=2)
        return ruta

    df = pd.DataFrame(transacciones)[columnas]
    if formato == "xlsx":
        try:
            df.to_excel(ruta, index=False)
            return ruta
        except Exception:
            formato = "csv"  # sin openpyxl caemos a csv sin romper la corrida
            ruta = f"{ruta_base}.csv"
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
    return ruta


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el dataset financiero sintetico.")
    parser.add_argument("--usuarios", type=int, default=400)
    parser.add_argument("--meses", type=int, default=6)
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument(
        "--salida", default=os.path.join(os.path.dirname(__file__), "..", "datos", "crudos")
    )
    args = parser.parse_args()

    rng = random.Random(args.semilla)
    salida = os.path.abspath(args.salida)
    os.makedirs(salida, exist_ok=True)

    fecha_base = datetime(2026, 1, 1)
    usuarios: list[dict] = []

    print(f"Generando {args.usuarios} usuarios x {args.meses} meses (semilla {args.semilla})...")

    for idx in range(1, args.usuarios + 1):
        usuario, transacciones = generar_usuario(idx, args.meses, fecha_base, rng)
        letra = MAPEO_LETRAS[usuario["perfil"]]
        formato = rng.choice(FORMATOS)
        ruta_base = os.path.join(salida, f"usuario_{usuario['usuario_id']}_{letra}")
        ruta = guardar(transacciones, ruta_base, formato)

        usuario["archivo"] = os.path.basename(ruta)
        usuario["n_transacciones"] = len(transacciones)
        usuarios.append(usuario)

    df_usuarios = pd.DataFrame(usuarios)
    ruta_usuarios = os.path.join(salida, "usuarios.csv")
    df_usuarios.to_csv(ruta_usuarios, index=False, encoding="utf-8")

    print(f"  {len(usuarios)} extractos escritos en {salida}")
    print(f"  metadatos de usuario -> {ruta_usuarios}")
    print(f"  total de transacciones: {int(df_usuarios['n_transacciones'].sum()):,}")
    print("\nDistribucion de perfiles:")
    print(df_usuarios["perfil"].value_counts().to_string())


if __name__ == "__main__":
    main()
