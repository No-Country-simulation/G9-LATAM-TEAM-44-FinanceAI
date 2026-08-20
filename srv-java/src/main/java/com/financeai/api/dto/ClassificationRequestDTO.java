package com.financeai.api.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.util.List;

/**
 * Peticion de clasificacion de transacciones.
 *
 * No pide ingreso ni endeudamiento: clasificar no los necesita, y pedir datos
 * sensibles que no se usan no tiene sentido.
 */
public record ClassificationRequestDTO(

        @NotNull(message = "La lista de transacciones es requerida")
        @Size(min = 1, max = 5000, message = "Se requiere entre 1 y 5000 transacciones")
        @Valid
        List<TransactionDTO> transacciones
) {}
