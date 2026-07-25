package com.financeai.api.integration.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/** Respuesta de POST /perfil. */
public record PerfilResponse(
        @JsonProperty("perfil_financiero") String perfilFinanciero,
        @JsonProperty("probabilidad") Double probabilidad,
        @JsonProperty("factores") List<FactorMl> factores
) {}
