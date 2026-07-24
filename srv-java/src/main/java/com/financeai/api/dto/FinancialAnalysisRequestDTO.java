package com.financeai.api.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import java.util.List;

public record FinancialAnalysisRequestDTO(
        @NotNull @Min(0) Double ingresoMensual,
        @NotNull @Min(0) Integer nivelEndeudamiento,
        @NotNull String frecuenciaAhorro,
        @NotNull @Valid List<TransactionDTO> transacciones
) {}
