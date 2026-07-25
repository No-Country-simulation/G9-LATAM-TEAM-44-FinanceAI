package com.financeai.api.service;

import com.financeai.api.dto.FactorDTO;

import java.util.List;

/**
 * Resultado interno de la evaluacion de perfil.
 *
 * @param modoDegradado true si se calculo con los umbrales locales porque
 *                      srv-python no respondio
 */
public record ProfileResult(
        String perfilFinanciero,
        Double probabilidad,
        List<FactorDTO> factores,
        boolean modoDegradado
) {}
