package com.financeai.api.integration;

import com.financeai.api.config.MlServiceProperties;
import com.financeai.api.integration.dto.ClasificarRequest;
import com.financeai.api.integration.dto.ClasificarResponse;
import com.financeai.api.integration.dto.PerfilRequest;
import com.financeai.api.integration.dto.PerfilResponse;
import com.financeai.api.integration.dto.TransaccionMl;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Cliente HTTP hacia srv-python.
 *
 * No lanza por fallo de red ni por error del servicio: devuelve
 * {@link Optional#empty()} y quien llama decide como degradar, para que una
 * caida del ml-service no acabe en un 5xx.
 *
 * Las llamadas van por lote, una peticion por analisis y no una por
 * transaccion.
 */
@Component
public class PythonModelClient {

    private static final Logger log = LoggerFactory.getLogger(PythonModelClient.class);

    private final RestClient restClient;
    private final MlServiceProperties properties;

    public PythonModelClient(RestClient mlRestClient, MlServiceProperties properties) {
        this.restClient = mlRestClient;
        this.properties = properties;
    }

    /** POST /clasificar — categoriza un lote de transacciones. */
    public Optional<ClasificarResponse> clasificar(List<TransaccionMl> transacciones) {
        if (!properties.enabled()) {
            log.debug("ml-service deshabilitado por configuracion; se usa el respaldo local.");
            return Optional.empty();
        }
        if (transacciones == null || transacciones.isEmpty()) {
            return Optional.empty();
        }

        try {
            ClasificarResponse respuesta = restClient.post()
                    .uri("/clasificar")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(new ClasificarRequest(transacciones))
                    .retrieve()
                    .body(ClasificarResponse.class);

            return Optional.ofNullable(respuesta);

        } catch (RestClientException e) {
            log.warn("ml-service /clasificar no disponible ({}: {}). Se activa el modo degradado.",
                    e.getClass().getSimpleName(), e.getMessage());
            return Optional.empty();
        }
    }

    /** POST /perfil — evalua el perfil financiero a partir de agregados. */
    public Optional<PerfilResponse> perfil(PerfilRequest peticion) {
        if (!properties.enabled()) {
            log.debug("ml-service deshabilitado por configuracion; se usa el respaldo local.");
            return Optional.empty();
        }

        try {
            PerfilResponse respuesta = restClient.post()
                    .uri("/perfil")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(peticion)
                    .retrieve()
                    .body(PerfilResponse.class);

            return Optional.ofNullable(respuesta);

        } catch (RestClientException e) {
            log.warn("ml-service /perfil no disponible ({}: {}). Se activa el modo degradado.",
                    e.getClass().getSimpleName(), e.getMessage());
            return Optional.empty();
        }
    }

    /** GET /health — para el endpoint de diagnostico de la API. */
    public boolean disponible() {
        if (!properties.enabled()) {
            return false;
        }
        try {
            restClient.get().uri("/health").retrieve().toBodilessEntity();
            return true;
        } catch (RestClientException e) {
            return false;
        }
    }

    /**
     * GET /modelo/info — procedencia y metricas del modelo cargado.
     *
     * Solo lo usa el endpoint de diagnostico, para saber que modelo esta
     * sirviendo sin entrar en el contenedor.
     */
    @SuppressWarnings("unchecked")
    public Optional<Map<String, Object>> infoModelo() {
        if (!properties.enabled()) {
            return Optional.empty();
        }
        try {
            return Optional.ofNullable(
                    restClient.get().uri("/modelo/info").retrieve().body(Map.class));
        } catch (RestClientException e) {
            return Optional.empty();
        }
    }

    /**
     * GET /modelo/metricas — resumen condensado de las metricas de evaluacion
     * del modelo (Fase 16): baseline, CV agrupada por comercio, matriz de
     * confusion OOD, metricas por categoria, calibracion y benchmark contra
     * modelos clasicos. Mismo patron que {@link #infoModelo()}: si el
     * ml-service no responde, se devuelve vacio y quien llama decide que
     * mostrar.
     */
    @SuppressWarnings("unchecked")
    public Optional<Map<String, Object>> metricasModelo() {
        if (!properties.enabled()) {
            return Optional.empty();
        }
        try {
            return Optional.ofNullable(
                    restClient.get().uri("/modelo/metricas").retrieve().body(Map.class));
        } catch (RestClientException e) {
            return Optional.empty();
        }
    }

    public String urlConfigurada() {
        return properties.url();
    }
}
