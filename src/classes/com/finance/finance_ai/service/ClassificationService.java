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
            String category = transaction.categoria();
            if (category == null || category.isBlank()) {
                category = modelClient.classify(transaction.descripcion());
            }
            summary.merge(category, transaction.valor(), Double::sum);
        }

        return summary;
    }
}
