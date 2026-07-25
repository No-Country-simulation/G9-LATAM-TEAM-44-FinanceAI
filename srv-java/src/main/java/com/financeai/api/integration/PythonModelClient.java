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
import java.util.Optional;

/**
 * Cliente HTTP hacia srv-python (el servicio de AI).
 *
 * Contrato de esta clase: NUNCA lanza por fallo de red o error del servicio.
 * Devuelve {@link Optional#empty()} y quien llama decide como degradar. Esa
 * decision es deliberada: una caida del ml-service no debe convertirse en un
 * 5xx para el usuario final.
 *
 * Las llamadas son POR LOTE (una peticion por analisis, no una por transaccion):
 * con 200 transacciones la version anterior habria hecho 200 round-trips.
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

    public String urlConfigurada() {
        return properties.url();
    }
}
