package com.financeai.api.controller;

import com.financeai.api.dto.ClassificationRequestDTO;
import com.financeai.api.dto.ClassificationResponseDTO;
import com.financeai.api.dto.ErrorResponseDTO;
import com.financeai.api.dto.FinancialAnalysisRequestDTO;
import com.financeai.api.dto.FinancialAnalysisResponseDTO;
import com.financeai.api.integration.OCIStorageService;
import com.financeai.api.integration.PythonModelClient;
import com.financeai.api.service.ClassificationResult;
import com.financeai.api.service.ClassificationService;
import com.financeai.api.service.FinancialAnalysisService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
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
    private final ClassificationService classificationService;
    private final PythonModelClient modelClient;
    private final OCIStorageService ociStorageService;

    public FinancialController(FinancialAnalysisService analysisService,
                               ClassificationService classificationService,
                               PythonModelClient modelClient,
                               OCIStorageService ociStorageService) {
        this.analysisService = analysisService;
        this.classificationService = classificationService;
        this.modelClient = modelClient;
        this.ociStorageService = ociStorageService;
    }

    @GetMapping("/health")
    @Operation(summary = "Liveness de la API (no consulta el ml-service)")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "ok"));
    }

    @GetMapping("/version")
    @Operation(summary = "Version del MVP")
    public ResponseEntity<Map<String, String>> version() {
        return ResponseEntity.ok(Map.of("version", "1.0.0-MVP"));
    }

    /**
     * Diagnostico de la integracion con srv-python. Va aparte de /health
     * porque ese es liveness y no debe hacer llamadas de red.
     */
    @GetMapping("/ml-status")
    @Operation(summary = "Verifica si el servicio de AI (srv-python) esta accesible")
    public ResponseEntity<Map<String, Object>> mlStatus() {
        boolean disponible = modelClient.disponible();

        Map<String, Object> cuerpo = new LinkedHashMap<>();
        cuerpo.put("ml_service_url", modelClient.urlConfigurada());
        cuerpo.put("disponible", disponible);
        cuerpo.put("modo", disponible ? "modelo" : "degradado (reglas locales)");
        cuerpo.put("modelo", modelClient.infoModelo().orElse(Map.of()));
        cuerpo.put("almacenamiento", ociStorageService.estado());
        return ResponseEntity.ok(cuerpo);
    }

    /**
     * Proxy hacia srv-python GET /modelo/metricas (Fase 16): resumen
     * condensado de las metricas de evaluacion del modelo (baseline, CV
     * agrupada, matriz de confusion OOD, metricas por categoria, calibracion
     * y benchmark), para que el frontend no tenga que hablar directo con el
     * ml-service. Mismo patron de proxy que {@link #mlStatus()}.
     */
    @GetMapping("/metricas-modelo")
    @Operation(summary = "Resumen de metricas de evaluacion del modelo (proxy a srv-python)")
    public ResponseEntity<Map<String, Object>> metricasModelo() {
        return ResponseEntity.ok(modelClient.metricasModelo().orElse(Map.of()));
    }

    @PostMapping("/analisis-financiero")
    @Operation(
            summary = "Analisis financiero completo",
            description = "Clasifica las transacciones, evalua el perfil financiero y genera "
                    + "recomendaciones personalizadas. Si el ml-service no responde, el "
                    + "resultado se calcula con reglas locales y se marca modo_degradado=true.")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Analisis generado"),
            @ApiResponse(responseCode = "400", description = "Error de validacion",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
    })
    public ResponseEntity<FinancialAnalysisResponseDTO> analizarFinanzas(
            @Valid @RequestBody FinancialAnalysisRequestDTO request) {

        return ResponseEntity.ok(analysisService.analyze(request));
    }

    /**
     * Clasificacion aislada, para consumidores que solo quieren categorizar un
     * extracto y no tienen por que aportar ingreso ni endeudamiento.
     */
    @PostMapping("/clasificar-transacciones")
    @Operation(
            summary = "Clasificacion de transacciones",
            description = "Categoriza un lote de transacciones y devuelve el detalle por "
                    + "transaccion junto al agregado por categoria. No requiere datos "
                    + "financieros del usuario.")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Transacciones clasificadas"),
            @ApiResponse(responseCode = "400", description = "Error de validacion",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
    })
    public ResponseEntity<ClassificationResponseDTO> clasificarTransacciones(
            @Valid @RequestBody ClassificationRequestDTO request) {

        ClassificationResult resultado = classificationService.classify(request.transacciones());

        return ResponseEntity.ok(new ClassificationResponseDTO(
                resultado.detalle(),
                resultado.resumenGastos(),
                redondear(resultado.totalGastos()),
                resultado.modoDegradado()
        ));
    }

    private double redondear(double valor) {
        return Math.round(valor * 100.0) / 100.0;
    }
}
