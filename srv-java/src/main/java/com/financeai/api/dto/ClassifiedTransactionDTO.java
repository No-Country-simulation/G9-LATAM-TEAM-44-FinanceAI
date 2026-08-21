package com.financeai.api.dto;

/**
 * Una transaccion ya categorizada.
 *
 * @param descripcion     descripcion original, tal cual llego
 * @param valor           monto original, no el que devuelve el modelo
 * @param categoria       una de las ocho categorias canonicas
 * @param confianza       0..1; por debajo del umbral la categoria pasa a "otras"
 * @param estadoConfianza "aceptado" | "requiere_revision" | "otras" (Fase 12,
 *                        estrategia de abstencion). Ver
 *                        {@link com.financeai.api.service.ClassificationService}
 *                        para los cortes y su justificacion.
 */
public record ClassifiedTransactionDTO(
        String descripcion,
        Double valor,
        String categoria,
        Double confianza,
        String estadoConfianza
) {}
