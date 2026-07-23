package com.financeai.api.integration;

import org.springframework.stereotype.Component;

@Component
public class OCIStorageService {

    public String getModelLocation() {
        return "oci://finance-ai-models/financial-model.pkl";
    }
}
