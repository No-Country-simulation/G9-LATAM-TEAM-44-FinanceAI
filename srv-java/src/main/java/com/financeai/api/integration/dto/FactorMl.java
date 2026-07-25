package com.financeai.api.integration.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/** Factor explicativo del perfil. {@code impacto} es "sube_riesgo" o "baja_riesgo". */
public record FactorMl(
        @JsonProperty("nombre") String nombre,
        @JsonProperty("valor") Double valor,
        @JsonProperty("impacto") String impacto
) {}
