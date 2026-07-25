package com.financeai.api.dto;

/**
 * Factor que explica el perfil devuelto.
 *
 * @param impacto "sube_riesgo" o "baja_riesgo"
 */
public record FactorDTO(
        String nombre,
        Double valor,
        String impacto
) {}
