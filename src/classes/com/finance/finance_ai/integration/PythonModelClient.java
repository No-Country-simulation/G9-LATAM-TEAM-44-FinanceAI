package com.financeai.api.integration;

import org.springframework.stereotype.Component;

@Component
public class PythonModelClient {

    public String classify(String descripcion) {
        String text = descripcion.toLowerCase();

        if (text.contains("supermercado") || text.contains("comida") || text.contains("restaurante")) return "alimentacion";
        if (text.contains("combustible") || text.contains("gasolina") || text.contains("uber") || text.contains("taxi")) return "transporte";
        if (text.contains("farmacia") || text.contains("hospital") || text.contains("salud")) return "salud";
        if (text.contains("arriendo") || text.contains("alquiler") || text.contains("hipoteca")) return "vivienda";
        if (text.contains("colegio") || text.contains("universidad") || text.contains("curso")) return "educacion";
        if (text.contains("netflix") || text.contains("cine") || text.contains("streaming")) return "ocio";
        if (text.contains("luz") || text.contains("agua") || text.contains("internet")) return "servicios";

        return "otras";
    }
}
