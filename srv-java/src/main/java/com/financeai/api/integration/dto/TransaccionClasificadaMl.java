package com.financeai.api.integration.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Transaccion ya categorizada por el modelo, con su nivel de confianza [0,1].
 *
 * {@code estadoConfianza} es lo que srv-python ya calculo (Fase 12); llega
 * informativo pero {@link com.financeai.api.service.ClassificationService}
 * recalcula el propio estado con los umbrales de {@code application.properties}
 * para no depender de que el ml-service este disponible (tambien se calcula en
 * modo degradado, donde este campo nunca llega).
 */
public record TransaccionClasificadaMl(
        @JsonProperty("descripcion") String descripcion,
        @JsonProperty("valor") Double valor,
        @JsonProperty("categoria") String categoria,
        @JsonProperty("confianza") Double confianza,
        @JsonProperty("estado_confianza") String estadoConfianza
) {}
