package com.financeai.api.integration;

import com.financeai.api.model.FinancialCategory;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Clasificador de respaldo por palabras clave.
 *
 * Entra cuando srv-python no responde, para seguir devolviendo un analisis en
 * vez de un 5xx.
 *
 * El diccionario es espejo de KEYWORDS en srv-python/app/reglas.py; las
 * palabras nuevas hay que anadirlas en ambos. El orden de iteracion importa:
 * gana la primera categoria que haga match, igual que en Python.
 */
@Component
public class FallbackClassifier {

    /** Confianza que se reporta cuando una keyword acierta. */
    public static final double CONFIANZA_KEYWORD = 0.90;

    /** Confianza cuando ninguna coincide y cae en "otras". */
    public static final double CONFIANZA_SIN_MATCH = 0.40;

    private static final Map<FinancialCategory, List<String>> KEYWORDS = new LinkedHashMap<>();

    static {
        KEYWORDS.put(FinancialCategory.ALIMENTACION, List.of(
                "supermercado", "comida", "restaurante", "mercado", "exito",
                "carulla", "d1", "panaderia", "rappi", "domicilio"));
        KEYWORDS.put(FinancialCategory.TRANSPORTE, List.of(
                "combustible", "gasolina", "uber", "taxi", "terpel", "peaje",
                "transmilenio", "metro", "parqueadero", "bus"));
        KEYWORDS.put(FinancialCategory.SALUD, List.of(
                "farmacia", "hospital", "salud", "drogueria", "eps", "medico",
                "clinica", "odontologia"));
        KEYWORDS.put(FinancialCategory.VIVIENDA, List.of(
                "arriendo", "alquiler", "hipoteca", "administracion", "renta"));
        KEYWORDS.put(FinancialCategory.EDUCACION, List.of(
                "colegio", "universidad", "curso", "matricula", "udemy",
                "platzi", "libros"));
        KEYWORDS.put(FinancialCategory.OCIO, List.of(
                "netflix", "cine", "streaming", "spotify", "disney", "hbo",
                "steam", "bar", "concierto", "juego"));
        KEYWORDS.put(FinancialCategory.SERVICIOS, List.of(
                "luz", "agua", "internet", "gas", "celular", "energia",
                "claro", "movistar", "tigo"));
    }

    public FinancialCategory clasificar(String descripcion) {
        if (descripcion == null || descripcion.isBlank()) {
            return FinancialCategory.OTRAS;
        }
        String texto = descripcion.toLowerCase(Locale.ROOT);

        for (Map.Entry<FinancialCategory, List<String>> entrada : KEYWORDS.entrySet()) {
            for (String palabra : entrada.getValue()) {
                if (texto.contains(palabra)) {
                    return entrada.getKey();
                }
            }
        }
        return FinancialCategory.OTRAS;
    }
}
