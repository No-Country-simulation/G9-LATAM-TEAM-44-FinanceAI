package com.financeai.api.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record TransactionDTO(
        @NotNull(message = "La descripción es requerida")
        String descripcion,

        @NotNull(message = "El valor es requerido")
        @Positive(message = "El valor debe ser mayor a 0")
        Double valor
) {}
