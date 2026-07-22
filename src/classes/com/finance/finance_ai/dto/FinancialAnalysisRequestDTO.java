package com.financeai.api.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.util.List;

public record FinancialAnalysisRequestDTO(
    @NotNull @DecimalMin(value = "0.0")
    Double ingresoMensual,

    @NotNull @DecimalMin(value = "0.0")
    Double nivelEndeudamiento,

    @NotBlank
    String frecuenciaAhorro,

    @NotEmpty(message = "Debe existir al menos una transacción")
    @Valid
    List<TransactionDTO> transacciones
) {}
