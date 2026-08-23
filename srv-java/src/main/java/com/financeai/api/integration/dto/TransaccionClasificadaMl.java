package com.financeai.api.integration.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * Transaccion ya categorizada por el modelo, con su nivel de confianza [0,1].
 *
 * {@code estadoConfianza} es lo que srv-python ya calculo (Fase 12); llega
 * informativo pero {@link com.financeai.api.service.ClassificationService}
 * recalcula el propio estado con los umbrales de {@code application.properties}
 * para no depender de que el ml-service este disponible (tambien se calcula en
 * modo degradado, donde este campo nunca llega).
 *
 * {@code top3} (Fase 16) trae hasta 3 categorias candidatas con su confianza,
 * en orden descendente; en modo reglas/degradado srv-python solo manda una.
 */
public record TransaccionClasificadaMl(
        @JsonProperty("descripcion") String descripcion,
        @JsonProperty("valor") Double valor,
        @JsonProperty("categoria") String categoria,
        @JsonProperty("confianza") Double confianza,
        @JsonProperty("estado_confianza") String estadoConfianza,
        @JsonProperty("top3") List<TopCategoriaMl> top3
) {

    /**
     * Constructor de compatibilidad con el codigo y los tests previos a la
     * Fase 16, que no conocian {@code top3}. Jackson deserializa con el
     * constructor canonico (el de 6 parametros): un JSON de srv-python sin
     * "top3" tambien deja este campo en {@code null} sin pasar por aqui.
     */
    public TransaccionClasificadaMl(String descripcion, Double valor, String categoria,
                                     Double confianza, String estadoConfianza) {
        this(descripcion, valor, categoria, confianza, estadoConfianza, null);
    }
}
