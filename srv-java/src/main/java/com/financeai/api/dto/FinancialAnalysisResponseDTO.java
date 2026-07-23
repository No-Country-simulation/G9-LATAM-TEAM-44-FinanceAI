package com.financeai.api.dto;

import java.util.List;
import java.util.Map;

public record FinancialAnalysisResponseDTO(
    String perfilFinanciero,
    Double probabilidad,
    Map<String, Double> resumenGastos,
    List<String> recomendaciones
) {}
