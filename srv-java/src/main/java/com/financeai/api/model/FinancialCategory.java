package com.financeai.api.model;

import java.util.Locale;

/**
 * Categorias canonicas del sistema.
 *
 * El valor en minuscula es el contrato compartido con srv-python (enum Categoria
 * en app/main.py) y con el JSON de respuesta. Nunca uses strings sueltos: pasa
 * siempre por {@link #getValor()} o {@link #desdeValor(String)}.
 */
public enum FinancialCategory {

    ALIMENTACION("alimentacion"),
    TRANSPORTE("transporte"),
    SALUD("salud"),
    VIVIENDA("vivienda"),
    EDUCACION("educacion"),
    OCIO("ocio"),
    SERVICIOS("servicios"),
    OTRAS("otras");

    private final String valor;

    FinancialCategory(String valor) {
        this.valor = valor;
    }

    public String getValor() {
        return valor;
    }

    /**
     * Convierte el valor recibido del modelo a una categoria canonica.
     * Si llega null, vacio o algo desconocido, degrada a {@link #OTRAS} en vez
     * de reventar: el backend nunca debe caerse por un valor inesperado del ML.
     */
    public static FinancialCategory desdeValor(String valor) {
        if (valor == null || valor.isBlank()) {
            return OTRAS;
        }
        String normalizado = valor.trim().toLowerCase(Locale.ROOT);
        for (FinancialCategory categoria : values()) {
            if (categoria.valor.equals(normalizado)) {
                return categoria;
            }
        }
        return OTRAS;
    }
}
