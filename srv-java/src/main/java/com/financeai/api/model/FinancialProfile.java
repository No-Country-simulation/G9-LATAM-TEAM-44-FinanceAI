package com.financeai.api.model;

import java.util.Locale;
import java.text.Normalizer;

/**
 * Perfiles financieros canonicos.
 *
 * El valor con tilde ("En observación") es el que devuelve la API y el que
 * espera el frontend. Usa {@link #getValor()} o {@link #desdeValor} en vez de
 * la cadena suelta.
 *
 * {@link #desdeValor} acepta la variante sin tilde porque el generador de datos
 * escribe "En observacion".
 */
public enum FinancialProfile {

    SALUDABLE("Saludable"),
    EN_OBSERVACION("En observación"),
    EN_RIESGO("En riesgo");

    private final String valor;

    FinancialProfile(String valor) {
        this.valor = valor;
    }

    public String getValor() {
        return valor;
    }

    /**
     * Resuelve el perfil sin importar tildes ni mayusculas.
     *
     * @return el perfil, o {@code null} si no corresponde a ninguno. Se
     *         devuelve null en vez de un valor por defecto para que quien
     *         llama decida si degradar.
     */
    public static FinancialProfile desdeValor(String valor) {
        if (valor == null || valor.isBlank()) {
            return null;
        }
        String normalizado = sinTildes(valor.trim().toLowerCase(Locale.ROOT));
        for (FinancialProfile perfil : values()) {
            if (sinTildes(perfil.valor.toLowerCase(Locale.ROOT)).equals(normalizado)) {
                return perfil;
            }
        }
        return null;
    }

    /** True si el valor corresponde a alguno de los tres perfiles. */
    public static boolean esValido(String valor) {
        return desdeValor(valor) != null;
    }

    private static String sinTildes(String texto) {
        return Normalizer.normalize(texto, Normalizer.Form.NFD)
                .replaceAll("\\p{InCombiningDiacriticalMarks}+", "");
    }
}
