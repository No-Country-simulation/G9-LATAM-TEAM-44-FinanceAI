package com.financeai.api.model;

import java.util.Locale;

/**
 * Categorias canonicas del sistema.
 *
 * El valor en minuscula es el que comparten srv-python (enum Categoria en
 * app/main.py) y el JSON de respuesta. Usa {@link #getValor()} o
 * {@link #desdeValor(String)} en vez de strings sueltos.
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
     * Null, vacio o desconocido degradan a {@link #OTRAS}: el backend no se cae
     * por un valor inesperado del ML.
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
