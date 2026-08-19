package com.financeai.api.dto;

import java.util.List;
import java.util.Map;

/**
 * Respuesta de la clasificacion de transacciones.
 *
 * El detalle alimenta la tabla del frontend y el resumen el grafico. Calcular
 * el resumen aqui evita que cada cliente lo reagregue y llegue a otro total.
 *
 * @param modoDegradado true si el resultado viene de las reglas locales
 */
public record ClassificationResponseDTO(
        List<ClassifiedTransactionDTO> transaccionesClasificadas,
        Map<String, Double> resumenGastos,
        Double totalGastos,
        Boolean modoDegradado
) {}
