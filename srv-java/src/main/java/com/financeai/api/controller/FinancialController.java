package com.financeai.api.controller;

import com.financeai.api.dto.FinancialAnalysisRequestDTO;
import com.financeai.api.dto.FinancialAnalysisResponseDTO;
import com.financeai.api.integration.PythonModelClient;
import com.financeai.api.service.FinancialAnalysisService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/v1")
@Tag(name = "Analisis financiero", description = "Orquestador de salud financiera")
public class FinancialController {

    private final FinancialAnalysisService analysisService;
    private final PythonModelClient modelClient;

    public FinancialController(FinancialAnalysisService analysisService,
                               PythonModelClient modelClient) {
        this.analysisService = analysisService;
        this.modelClient = modelClient;
    }

    @GetMapping("/health")
    @Operation(summary = "Liveness de la API (no consulta el ml-service)")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "ok"));
    }

    @GetMapping("/version")
    public ResponseEntity<Map<String, String>> version() {
        return ResponseEntity.ok(Map.of("version", "1.0.0-MVP"));
    }

    /**
     * Diagnostico de la integracion con srv-python. Separado de /health a
     * proposito: /health es liveness y no debe hacer llamadas de red.
     */
    @GetMapping("/ml-status")
    @Operation(summary = "Verifica si el servicio de AI (srv-python) esta accesible")
    public ResponseEntity<Map<String, Object>> mlStatus() {
        boolean disponible = modelClient.disponible();

        Map<String, Object> cuerpo = new LinkedHashMap<>();
        cuerpo.put("ml_service_url", modelClient.urlConfigurada());
        cuerpo.put("disponible", disponible);
        cuerpo.put("modo", disponible ? "modelo" : "degradado (reglas locales)");
        return ResponseEntity.ok(cuerpo);
    }

    @PostMapping("/analisis-financiero")
    @Operation(summary = "Clasifica las transacciones, evalua el perfil y genera recomendaciones")
    public ResponseEntity<FinancialAnalysisResponseDTO> analizarFinanzas(
            @Valid @RequestBody FinancialAnalysisRequestDTO request) {

        return ResponseEntity.ok(analysisService.analyze(request));
    }
}
