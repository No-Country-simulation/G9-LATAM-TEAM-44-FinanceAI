package com.financeai.api.integration.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Transaccion tal como la espera srv-python en POST /clasificar.
 *
 * Los nombres JSON van con @JsonProperty explicito para que este contrato NO
 * dependa de spring.jackson.property-naming-strategy: si alguien cambia esa
 * propiedad global, la integracion sigue funcionando.
 */
public record TransaccionMl(
        @JsonProperty("descripcion") String descripcion,
        @JsonProperty("valor") Double valor
) {}
