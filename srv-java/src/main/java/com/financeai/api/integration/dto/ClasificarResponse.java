package com.financeai.api.integration.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/** Respuesta de POST /clasificar. */
public record ClasificarResponse(
        @JsonProperty("transacciones_clasificadas") List<TransaccionClasificadaMl> transaccionesClasificadas
) {}
