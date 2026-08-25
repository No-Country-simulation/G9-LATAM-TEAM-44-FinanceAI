package com.financeai.api.dto;

import java.util.List;
import java.util.Map;

/**
 * Respuesta del analisis financiero.
 *
 * Se serializa en snake_case por spring.jackson.property-naming-strategy:
 * perfil_financiero, resumen_gastos, modo_degradado...
 *
 * @param factores                  explicabilidad del perfil (que empuja el
 *                                  riesgo y hacia donde)
 * @param transaccionesClasificadas una entrada por transaccion recibida, en el
 *                                  mismo orden, con su categoria y su confianza.
 *                                  Sale de la misma llamada al modelo que el
 *                                  resumen, asi que no cuesta una clasificacion
 *                                  extra. Permite ver que hay dentro de cada
 *                                  porcion del grafico en vez de tener que
 *                                  fiarse del total
 * @param modoDegradado             true si el ml-service no respondio y el
 *                                  resultado se calculo con las reglas locales
 */
public record FinancialAnalysisResponseDTO(
        String perfilFinanciero,
        Double probabilidad,
        Map<String, Double> resumenGastos,
        List<String> recomendaciones,
        List<FactorDTO> factores,
        List<ClassifiedTransactionDTO> transaccionesClasificadas,
        Boolean modoDegradado
) {}
