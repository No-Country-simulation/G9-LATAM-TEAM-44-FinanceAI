package com.financeai.api.integration.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Una entrada del top3 que envia srv-python dentro de
 * {@link TransaccionClasificadaMl#top3()} (Fase 16): una categoria candidata
 * y la confianza que le asigno el modelo (o la regla, en modo degradado).
 */
public record TopCategoriaMl(
        @JsonProperty("categoria") String categoria,
        @JsonProperty("confianza") Double confianza
) {}
