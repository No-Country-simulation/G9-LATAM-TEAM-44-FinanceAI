package com.financeai.api.controller;

import com.financeai.api.dto.FinancialAnalysisRequestDTO;
import com.financeai.api.dto.FinancialAnalysisResponseDTO;
import com.financeai.api.dto.TransactionDTO;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1")
public class FinancialController {

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "ok"));
    }

    @GetMapping("/version")
    public ResponseEntity<Map<String, String>> version() {
        return ResponseEntity.ok(Map.of("version", "1.0.0-MVP"));
    }

    @PostMapping("/analisis-financiero")
    public ResponseEntity<FinancialAnalysisResponseDTO> analizarFinanzas(
            @Valid @RequestBody FinancialAnalysisRequestDTO request) {

        // Respuesta MOCK estática para validar conectividad y serialización JSON (SNAKE_CASE)
        Map<String, Double> resumen = Map.of(
                "alimentacion", 420.0,
                "transporte", 300.0,
                "entretenimiento", 40.0
        );

        List<String> recomendaciones = List.of(
                "Monitorear gastos recurrentes de entretenimiento",
                "Aumentar reserva financiera mensual"
        );

        FinancialAnalysisResponseDTO response = new FinancialAnalysisResponseDTO(
                "En observación",
                0.82,
                resumen,
                recomendaciones
        );

        return ResponseEntity.ok(response);
    }
}
