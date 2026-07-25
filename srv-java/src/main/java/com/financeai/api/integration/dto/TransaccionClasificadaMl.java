package com.financeai.api.integration.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/** Transaccion ya categorizada por el modelo, con su nivel de confianza [0,1]. */
public record TransaccionClasificadaMl(
        @JsonProperty("descripcion") String descripcion,
        @JsonProperty("valor") Double valor,
        @JsonProperty("categoria") String categoria,
        @JsonProperty("confianza") Double confianza
) {}
