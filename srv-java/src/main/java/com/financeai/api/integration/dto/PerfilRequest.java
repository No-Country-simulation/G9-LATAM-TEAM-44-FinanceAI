package com.financeai.api.integration.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Map;

/**
 * Cuerpo de POST /perfil.
 *
 * Particion "necesidad de saber": aqui viajan SOLO agregados.
 * Nunca las descripciones crudas de las transacciones.
 */
public record PerfilRequest(
        @JsonProperty("ingreso_mensual") Double ingresoMensual,
        @JsonProperty("nivel_endeudamiento") Integer nivelEndeudamiento,
        @JsonProperty("frecuencia_ahorro") String frecuenciaAhorro,
        @JsonProperty("resumen_gastos") Map<String, Double> resumenGastos
) {}
