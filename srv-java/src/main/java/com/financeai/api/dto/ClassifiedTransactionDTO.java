package com.financeai.api.dto;

import java.util.List;

/**
 * Una transaccion ya categorizada.
 *
 * @param descripcion     descripcion original, tal cual llego
 * @param valor           monto original, no el que devuelve el modelo
 * @param categoria       una de las nueve categorias canonicas
 * @param confianza       0..1; por debajo del umbral la categoria pasa a "otras"
 * @param estadoConfianza "aceptado" | "requiere_revision" | "otras" (Fase 12,
 *                        estrategia de abstencion). Ver
 *                        {@link com.financeai.api.service.ClassificationService}
 *                        para los cortes y su justificacion.
 * @param top3            hasta 3 categorias candidatas con su confianza, en
 *                         orden descendente y con {@code categoria} siempre
 *                         de primera (Fase 16). En modo reglas/degradado
 *                         trae un solo elemento. Ver
 *                         {@link com.financeai.api.service.ClassificationService}.
 */
public record ClassifiedTransactionDTO(
        String descripcion,
        Double valor,
        String categoria,
        Double confianza,
        String estadoConfianza,
        List<TopCategoryDTO> top3
) {

    /**
     * Constructor de compatibilidad con el codigo y los tests previos a la
     * Fase 16, que no conocian {@code top3}.
     */
    public ClassifiedTransactionDTO(String descripcion, Double valor, String categoria,
                                     Double confianza, String estadoConfianza) {
        this(descripcion, valor, categoria, confianza, estadoConfianza, List.of());
    }
}
