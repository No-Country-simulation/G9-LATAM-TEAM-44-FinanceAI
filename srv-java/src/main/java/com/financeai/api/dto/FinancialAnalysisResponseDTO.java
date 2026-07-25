package com.financeai.api.dto;

import java.util.List;
import java.util.Map;

/**
 * Respuesta del analisis financiero.
 *
 * Se serializa en snake_case por spring.jackson.property-naming-strategy:
 * perfil_financiero, resumen_gastos, modo_degradado...
 *
 * @param factores      explicabilidad del perfil (que empuja el riesgo y hacia donde)
 * @param modoDegradado true si el ml-service no respondio y el resultado se
 *                      calculo con las reglas de respaldo locales
 */
public record FinancialAnalysisResponseDTO(
        String perfilFinanciero,
        Double probabilidad,
        Map<String, Double> resumenGastos,
        List<String> recomendaciones,
        List<FactorDTO> factores,
        Boolean modoDegradado
) {}
