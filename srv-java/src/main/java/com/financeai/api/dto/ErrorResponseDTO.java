package com.financeai.api.dto;

import java.time.LocalDateTime;
import java.util.Map;

public record ErrorResponseDTO(
        String mensaje,
        Integer codigoEstado,
        LocalDateTime timestamp,
        Map<String, String> detalles
) {}
