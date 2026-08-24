package com.financeai.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.time.Duration;

/**
 * Configuracion del servicio de AI (srv-python).
 *
 * Se enlaza con el prefijo {@code ml.service} de application.properties. Todos
 * los valores tienen default para que la app arranque aunque no se declaren.
 */
@ConfigurationProperties(prefix = "ml.service")
public record MlServiceProperties(
        String url,
        Boolean enabled,
        Duration connectTimeout,
        Duration readTimeout,
        Double confianzaMinima,
        Double confianzaAlta
) {

    public MlServiceProperties {
        if (url == null || url.isBlank()) {
            url = "http://localhost:8000";
        }
        if (enabled == null) {
            enabled = Boolean.TRUE;
        }
        if (connectTimeout == null) {
            connectTimeout = Duration.ofSeconds(1);
        }
        if (readTimeout == null) {
            readTimeout = Duration.ofSeconds(2);
        }
        // Por debajo de este umbral, la categoria del modelo pasa a "otras".
        if (confianzaMinima == null || confianzaMinima < 0 || confianzaMinima > 1) {
            confianzaMinima = 0.5;
        }
        // Por encima de este umbral, el estado_confianza pasa a "aceptado".
        // Espejo de RegistroModelos.umbral_confianza_alta en srv-python
        // (app/modelos.py): 0.8 sale de ciencia-datos/experimentos/
        // calibracion.json, Fase 5 (ver ClassificationService para el detalle
        // de las cifras).
        if (confianzaAlta == null || confianzaAlta < 0 || confianzaAlta > 1) {
            confianzaAlta = 0.8;
        }
    }
}
