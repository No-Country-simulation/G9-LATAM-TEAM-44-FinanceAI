package com.financeai.api.controller;

import com.financeai.api.dto.FinancialAnalysisRequestDTO;
import com.financeai.api.dto.FinancialAnalysisResponseDTO;
import com.financeai.api.service.FinancialAnalysisService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1")
public class FinancialController {

    private final FinancialAnalysisService financialAnalysisService;

    public FinancialController(FinancialAnalysisService financialAnalysisService) {
        this.financialAnalysisService = financialAnalysisService;
    }

    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("Finance AI API is running");
    }

    @GetMapping("/version")
    public ResponseEntity<String> version() {
        return ResponseEntity.ok("1.0.0-MVP");
    }

    @PostMapping("/analisis-financiero")
    public ResponseEntity<FinancialAnalysisResponseDTO> analyze(
            @Valid @RequestBody FinancialAnalysisRequestDTO request) {
        return ResponseEntity.ok(financialAnalysisService.analyze(request));
    }
}
