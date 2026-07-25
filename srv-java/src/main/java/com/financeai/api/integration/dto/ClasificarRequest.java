package com.financeai.api.integration.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * Cuerpo de POST /clasificar.
 *
 * Particion "necesidad de saber": aqui viajan SOLO las transacciones.
 * Nunca el ingreso, la deuda ni datos de identidad.
 */
public record ClasificarRequest(
        @JsonProperty("transacciones") List<TransaccionMl> transacciones
) {}
