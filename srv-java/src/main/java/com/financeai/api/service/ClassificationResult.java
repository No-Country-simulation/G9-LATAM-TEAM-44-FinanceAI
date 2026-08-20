package com.financeai.api.service;

import com.financeai.api.dto.ClassifiedTransactionDTO;

import java.util.List;
import java.util.Map;

/**
 * Resultado interno de la clasificacion.
 *
 * Trae el detalle por transaccion (para el endpoint de clasificacion) y el
 * agregado por categoria (para el analisis financiero). Salen de la misma
 * llamada al modelo; separarlos obligaria a clasificar dos veces.
 *
 * @param detalle        una entrada por transaccion recibida, en el mismo orden
 * @param resumenGastos  total gastado por categoria canonica
 * @param modoDegradado  true si se resolvio con el respaldo local porque
 *                       srv-python no respondio o devolvio algo incoherente
 */
public record ClassificationResult(
        List<ClassifiedTransactionDTO> detalle,
        Map<String, Double> resumenGastos,
        boolean modoDegradado
) {

    /** Suma de todo lo gastado, sin importar la categoria. */
    public double totalGastos() {
        return resumenGastos.values().stream()
                .mapToDouble(Double::doubleValue)
                .sum();
    }
}
