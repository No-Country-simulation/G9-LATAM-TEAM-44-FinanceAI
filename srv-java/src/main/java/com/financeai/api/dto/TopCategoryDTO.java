package com.financeai.api.dto;

/**
 * Una categoria candidata dentro de {@link ClassifiedTransactionDTO#top3()}
 * (Fase 16): la categoria en si y la confianza [0,1] que le asigno el modelo
 * (o la regla, en modo degradado).
 */
public record TopCategoryDTO(String categoria, Double confianza) {}
