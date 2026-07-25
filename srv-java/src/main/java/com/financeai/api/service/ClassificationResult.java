package com.financeai.api.service;

import java.util.Map;

/**
 * Resultado interno de la clasificacion.
 *
 * @param resumenGastos  total gastado por categoria canonica
 * @param modoDegradado  true si se resolvio con el respaldo local porque
 *                       srv-python no respondio o devolvio algo incoherente
 */
public record ClassificationResult(
        Map<String, Double> resumenGastos,
        boolean modoDegradado
) {}
