package com.financeai.api.dto;

import java.time.Instant;
import java.util.Map;

public record ErrorResponseDTO(
    Instant timestamp,
    int status,
    String error,
    String message,
    Map<String, String> detalles
) {}
