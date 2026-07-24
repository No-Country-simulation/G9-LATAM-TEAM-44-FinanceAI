package com.financeai.api.service;

import com.financeai.api.dto.TransactionDTO;
import com.financeai.api.integration.PythonModelClient;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class ClassificationService {

    private final PythonModelClient modelClient;

    public ClassificationService(PythonModelClient modelClient) {
        this.modelClient = modelClient;
    }

    public Map<String, Double> classify(List<TransactionDTO> transactions) {
        Map<String, Double> summary = new LinkedHashMap<>();

        for (TransactionDTO transaction : transactions) {
            // Se obtiene la categoría llamando al cliente ML
            String category = modelClient.classify(transaction.descripcion());

            // Manejo por si el cliente retorna nulo o vacío
            if (category == null || category.isBlank()) {
                category = "OTROS";
            }

            // Agrupa y suma el valor por categoría
            summary.merge(category, transaction.valor(), Double::sum);
        }

        return summary;
    }
}