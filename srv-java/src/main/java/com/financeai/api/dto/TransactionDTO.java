package com.financeai.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

/**
 * Una transaccion del extracto.
 * Restricciones alineadas con el modelo Transaccion de srv-python.
 */
public record TransactionDTO(

        // Python: descripcion = Field(min_length=1, max_length=200)
        @NotBlank(message = "La descripción es requerida")
        @Size(max = 200, message = "La descripción no puede superar los 200 caracteres")
        String descripcion,

        // Python: valor = Field(gt=0)
        @NotNull(message = "El valor es requerido")
        @Positive(message = "El valor debe ser mayor a 0")
        Double valor
) {}
