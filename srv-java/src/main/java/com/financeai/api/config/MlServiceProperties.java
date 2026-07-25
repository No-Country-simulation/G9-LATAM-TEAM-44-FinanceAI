package com.financeai.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.time.Duration;

/**
 * Configuracion del servicio de AI (srv-python).
 *
 * Se enlaza con el prefijo {@code ml.service} de application.properties.
 * Todos los valores tienen defaults sensatos para que la app arranque aunque
 * el archivo de propiedades no los declare.
 */
@ConfigurationProperties(prefix = "ml.service")
public record MlServiceProperties(
        String url,
        Boolean enabled,
        Duration connectTimeout,
        Duration readTimeout,
        Double confianzaMinima
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
        // Por debajo de este umbral la categoria devuelta por el modelo se
        // degrada a "otras": preferimos no clasificar antes que clasificar mal.
        if (confianzaMinima == null || confianzaMinima < 0 || confianzaMinima > 1) {
            confianzaMinima = 0.5;
        }
    }
}
