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
 * Es el plan B cuando srv-python no responde (flujo alternativo A2 del caso de
 * uso): la API sigue devolviendo un analisis util en vez de un error 5xx.
 *
 * El diccionario es un espejo de KEYWORDS en srv-python/app/main.py. Si alli se
 * agregan palabras, agregalas aqui tambien para que el modo degradado siga
 * dando resultados equivalentes. El orden de iteracion importa: gana la primera
 * categoria que haga match, igual que en Python.
 */
@Component
public class FallbackClassifier {

    /** Confianza que reportamos en modo degradado cuando hay match por keyword. */
    public static final double CONFIANZA_KEYWORD = 0.90;

    /** Confianza cuando ninguna keyword coincide y cae en "otras". */
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
