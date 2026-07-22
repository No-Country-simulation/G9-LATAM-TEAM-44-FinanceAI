package com.financeai.api.service;

import com.financeai.api.dto.FinancialAnalysisRequestDTO;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
public class RecommendationService {

    public List<String> generateRecommendations(
            FinancialAnalysisRequestDTO request,
            Map<String, Double> summary) {

        List<String> recommendations = new ArrayList<>();

        double income = request.ingresoMensual();
        double totalExpenses = summary.values().stream().mapToDouble(Double::doubleValue).sum();

        if (income > 0 && totalExpenses / income > 0.8) {
            recommendations.add("Revisar gastos totales: superan el 80% del ingreso mensual.");
        }

        if (request.nivelEndeudamiento() >= 40) {
            recommendations.add("Reducir el nivel de endeudamiento y priorizar obligaciones financieras.");
        }

        if ("Baja".equalsIgnoreCase(request.frecuenciaAhorro())) {
            recommendations.add("Aumentar la frecuencia de ahorro y crear una reserva financiera.");
        }

        if (recommendations.isEmpty()) {
            recommendations.add("Mantener el control de gastos y continuar monitoreando la evolución financiera.");
        }

        return recommendations;
    }
}
