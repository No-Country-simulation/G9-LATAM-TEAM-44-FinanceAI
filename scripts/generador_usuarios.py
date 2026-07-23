import os
import json
import random
import pandas as pd
from datetime import datetime, timedelta

# CONFIGURACION 
NUM_USUARIOS = 5
MESES_HISTORIAL = 6
CARPETA_SALIDA = "archivos_financieros_usuarios"

if not os.path.exists(CARPETA_SALIDA):
    os.makedirs(CARPETA_SALIDA)

FORMATOS_DISPONIBLES = ["json", "csv", "xlsx"]
MAPEO_LETRAS = {"Saludable": "S", "En observacion": "O", "En riesgo": "R"}

# ESTRUCTURA
catalogos_fijos_mensuales = {
    "Vivienda": ["Pago Luz Enel", "Servicio Agua Potable", "Gas Natural", "Administracion Edificio", "Arriendo Mensual"],
    "Servicios": ["Claro Telefonia Movil Plan", "Movistar Internet Hogar"],
    "Ocio": ["Netflix Streaming Mensual", "Spotify Premium", "Gimnasio SmartFit"]
}

catalogos_anuales = {
    "Servicios": ["Suscripcion Amazon Prime Anual", "Renovacion Hosting Web"],
    "Vivienda": ["Seguro Hogar Anual", "Impuesto Predial"]
}

catalogos_variables = {
    "Alimentacion": ["Supermercado Exito", "Walmart Express", "OXXO Tienda", "JUMBO SUPER", "McDonalds", "Rappi Comida", "Uber Eats"],
    "Transporte": ["Gasolinera Primax", "Gasolinera Pemex", "Uber Trip", "DiDi Ride", "Recarga Tarjeta Metro", "Taller Mecanico"],
    "Salud": ["Farmacia San Pablo", "Drogueria Cruz Verde", "Consulta Medica", "Laboratorio Clinico"],
    "Ocio": ["Cinepolis Entradas", "Steam Games", "Bar El Callejon", "Restaurante Gourmet"],
    "Educacion": ["Curso Udemy Online", "Libreria Panamericana"]
}

catalogos_ingresos = ["PAGO NOMINA / SUELDO", "TRANSFERENCIA DEPOSITO SALARIO"]
catalogos_deudas = ["PAGO TARJETA DE CREDITO", "CUOTA PRESTAMO BANCARIO", "CREDITO HIPOTECARIO", "PAGO PRESTAMO AUTOMOTRIZ", "ABONO EXTRAORDINARIO HIPOTECA"]

caracteres_basura = ["#", "*", "$$", "%", "///", "---", "  ERR:"]

def inyectar_ruido_texto(texto):
    if random.random() < 0.20: texto = texto.upper()
    elif random.random() < 0.35: texto = texto.lower()
    if random.random() < 0.25: texto = f"{random.choice(caracteres_basura)} {texto}"
    if random.random() < 0.20: texto = f"TRF/POS {texto}"
    return texto

perfiles_posibles = ["Saludable", "En observacion", "En riesgo"]
fecha_inicio_base = datetime(2026, 1, 1)

print(f"Generando {NUM_USUARIOS} archivos con logica de suscripciones e ingresos consistentes...")

for idx in range(1, NUM_USUARIOS + 1):
    seq_str = f"{idx:03d}"
    formato_elegido = random.choice(FORMATOS_DISPONIBLES)
    perfil_asignado = random.choice(perfiles_posibles)
    letra_perfil = MAPEO_LETRAS[perfil_asignado]
    
    ingreso_mensual_base = round(random.uniform(1500, 6000), 2)
    pagos_por_mes = random.choice([1, 2])
    monto_por_pago = round(ingreso_mensual_base / pagos_por_mes, 2)
    dias_pago = [1] if pagos_por_mes == 1 else [1, 15]
    
    if perfil_asignado == "Saludable":
        factor_gasto = random.uniform(0.50, 0.70)
    elif perfil_asignado == "En observacion":
        factor_gasto = random.uniform(0.80, 0.98)
    else: 
        factor_gasto = random.uniform(1.05, 1.40)

    gastos_fijos_usuario = []
    for cat in catalogos_fijos_mensuales:
        seleccionados = random.sample(catalogos_fijos_mensuales[cat], random.randint(1, 2))
        for item in seleccionados:
            monto_fijo = round(random.uniform(15.0, 80.0) if cat != "Vivienda" else random.uniform(50.0, 300.0), 2)
            dia_cobro = random.randint(1, 28)
            gastos_fijos_usuario.append({"desc": item, "monto": monto_fijo, "dia": dia_cobro})

    mes_gasto_anual = random.randint(0, MESES_HISTORIAL - 1)
    cat_anual = random.choice(list(catalogos_anuales.keys()))
    desc_anual = random.choice(catalogos_anuales[cat_anual])
    monto_anual = round(random.uniform(90.0, 250.0), 2)

    transacciones_usuario = []
    for mes_idx in range(MESES_HISTORIAL):
        mes_actual = fecha_inicio_base + timedelta(days=mes_idx * 30)
        str_mes = mes_actual.strftime("%Y-%m")
        gasto_acumulado_mes = 0
        
        # 1. INGRESOS
        for dia in dias_pago:
            transacciones_usuario.append({
                "fecha": mes_actual.replace(day=dia).strftime("%Y-%m-%d"),
                "tipo": "ingresos",
                "descripcion": inyectar_ruido_texto(random.choice(catalogos_ingresos)),
                "monto": monto_por_pago
            })
            
        # 2. GASTOS FIJOS
        for fijo in gastos_fijos_usuario:
            fecha_str = mes_actual.replace(day=fijo["dia"]).strftime("%Y-%m-%d")
            if random.random() < 0.10: fecha_str = mes_actual.replace(day=fijo["dia"]).strftime("%d/%m/%Y")
            
            transacciones_usuario.append({
                "fecha": fecha_str,
                "tipo": "egresos",
                "descripcion": inyectar_ruido_texto(fijo["desc"]),
                "monto": fijo["monto"]
            })
            gasto_acumulado_mes += fijo["monto"]

        # 3. GASTO ANUAL
        if mes_idx == mes_gasto_anual:
            transacciones_usuario.append({
                "fecha": mes_actual.replace(day=random.randint(1, 28)).strftime("%Y-%m-%d"),
                "tipo": "egresos",
                "descripcion": inyectar_ruido_texto(desc_anual),
                "monto": monto_anual
            })
            gasto_acumulado_mes += monto_anual

        # 4. GASTOS VARIABLES
        meta_gasto_mes = ingreso_mensual_base * factor_gasto
        presupuesto_variable = max(0, meta_gasto_mes - gasto_acumulado_mes)
        
        cant_variables = random.randint(10, 25) 
        if presupuesto_variable > 0:
            monto_promedio_var = presupuesto_variable / cant_variables
            for _ in range(cant_variables):
                cat_var = random.choice(list(catalogos_variables.keys()))
                desc_var = random.choice(catalogos_variables[cat_var])
                monto_var = round(random.uniform(monto_promedio_var * 0.3, monto_promedio_var * 1.8), 2)
                
                if random.random() < 0.02: monto_var = monto_var * -1

                fecha_var = mes_actual.replace(day=random.randint(1, 28))
                prob_fecha = random.random()
                if prob_fecha < 0.15: fecha_str = fecha_var.strftime("%d/%m/%Y")
                elif prob_fecha < 0.20: fecha_str = None
                else: fecha_str = fecha_var.strftime("%Y-%m-%d")

                transacciones_usuario.append({
                    "fecha": fecha_str, 
                    "tipo": "egresos",
                    "descripcion": inyectar_ruido_texto(desc_var) if random.random() > 0.03 else None,
                    "monto": monto_var
                })
        
        # 5. DEUDAS
        if random.random() < 0.15:
            monto_deuda = round(random.uniform(500.0, 3500.0), 2)
            transacciones_usuario.append({
                "fecha": mes_actual.replace(day=random.randint(1, 28)).strftime("%Y-%m-%d"),
                "tipo": "deudas",
                "descripcion": inyectar_ruido_texto(random.choice(catalogos_deudas)),
                "monto": monto_deuda
            })

    # GUARDAR ARCHIVOS (fecha/ tipo/ descripcion/ monto)
    
    nombre_archivo = f"usuario_{seq_str}_{letra_perfil}.{formato_elegido}"
    filepath = os.path.join(CARPETA_SALIDA, nombre_archivo)

    if formato_elegido == "json":
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(transacciones_usuario, f, ensure_ascii=False, indent=2)

    elif formato_elegido in ["csv", "xlsx"]:
        df_tx = pd.DataFrame(transacciones_usuario)
        
        # Asegurar solo las 4 columnas solicitadas
        df_tx = df_tx[["fecha", "tipo", "descripcion", "monto"]]
        
        if formato_elegido == "csv": 
            df_tx.to_csv(filepath, index=False, encoding="utf-8-sig")
        else:
            try: 
                df_tx.to_excel(filepath, index=False)
            except Exception:
                filepath = os.path.join(CARPETA_SALIDA, f"usuario_{seq_str}_{letra_perfil}.csv")
                df_tx.to_csv(filepath, index=False, encoding="utf-8-sig")

    print(f" --> Creado: {nombre_archivo}")

print("Proceso finalizado. El dataset esta listo para buscar patrones.")