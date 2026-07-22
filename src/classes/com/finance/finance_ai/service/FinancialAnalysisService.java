package com.financeai.api.service;

import com.financeai.api.dto.FinancialAnalysisRequestDTO;
import com.financeai.api.dto.FinancialAnalysisResponseDTO;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

@Service
public class FinancialAnalysisService {

    private final ClassificationService classificationService;
    private final RecommendationService recommendationService;

    public FinancialAnalysisService(
            ClassificationService classificationService,
            RecommendationService recommendationService) {
        this.classificationService = classificationService;
        this.recommendationService = recommendationService;
    }

    public FinancialAnalysisResponseDTO analyze(FinancialAnalysisRequestDTO request) {
        Map<String, Double> summary = classificationService.classify(request.transacciones());
        List<String> recommendations = recommendationService.generateRecommendations(request, summary);

        double ratio = request.ingresoMensual() == 0 ? 1.0 :
                summary.values().stream().mapToDouble(Double::doubleValue).sum() / request.ingresoMensual();

        String profile;
        if (request.nivelEndeudamiento() >= 50 || ratio >= 1.0) {
            profile = "En riesgo";
        } else if (request.nivelEndeudamiento() >= 30 || ratio >= 0.8) {
            profile = "En observación";
        } else {
            profile = "Saludable";
        }

        double probability = profile.equals("Saludable") ? 0.90 :
                profile.equals("En observación") ? 0.82 : 0.75;

        return new FinancialAnalysisResponseDTO(profile, probability, summary, recommendations);
    }
}
