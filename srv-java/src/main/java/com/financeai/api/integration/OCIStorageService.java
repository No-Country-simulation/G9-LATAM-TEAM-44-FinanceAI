package com.financeai.api.integration;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.financeai.api.config.OciProperties;
import com.financeai.api.dto.FinancialAnalysisRequestDTO;
import com.financeai.api.dto.FinancialAnalysisResponseDTO;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.TimeUnit;

/**
 * Persistencia de los analisis en OCI Object Storage.
 *
 * Cada analisis se guarda como un objeto JSON en
 * {@code <prefijo>/AAAA/MM/DD/<timestamp>-<id>.json}. Object Storage no tiene
 * indices, asi que el prefijo por dia es lo que permite recuperar despues un
 * rango de fechas sin listar el bucket entero.
 *
 * Esta clase ni lanza ni bloquea: el archivado es un efecto secundario y va en
 * un hilo aparte, de modo que un fallo o una latencia de Object Storage no
 * afectan a la respuesta.
 */
@Component
public class OCIStorageService {

    private static final Logger log = LoggerFactory.getLogger(OCIStorageService.class);

    private static final DateTimeFormatter RUTA_FECHA =
            DateTimeFormatter.ofPattern("yyyy/MM/dd").withZone(ZoneOffset.UTC);
    private static final DateTimeFormatter MARCA_TIEMPO =
            DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss").withZone(ZoneOffset.UTC);

    private final OciProperties properties;
    private final ObjectMapper objectMapper;
    private final RestClient restClient;

    /**
     * Un solo hilo daemon: suficiente para el volumen del MVP y acotado, para
     * que una caida de Object Storage no acumule tareas hasta agotar memoria.
     */
    private final ExecutorService ejecutor = Executors.newSingleThreadExecutor(tarea -> {
        Thread hilo = new Thread(tarea, "oci-historial");
        hilo.setDaemon(true);
        return hilo;
    });

    public OCIStorageService(OciProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
        this.restClient = RestClient.builder().build();
    }

    /** URI del modelo en Object Storage, el que descarga srv-python. */
    public String getModelLocation() {
        return "oci://" + properties.bucket() + "/clasificador_gastos.joblib";
    }

    /** Estado de la integracion, para exponerlo en /ml-status. */
    public Map<String, Object> estado() {
        Map<String, Object> estado = new LinkedHashMap<>();
        estado.put("proveedor", "OCI Object Storage");
        estado.put("bucket", properties.bucket());
        estado.put("namespace", properties.namespace());
        estado.put("region", properties.region());
        estado.put("historial_habilitado", properties.puedeEscribir());
        estado.put("modelo", getModelLocation());
        return estado;
    }

    /**
     * Archiva un analisis. Devuelve el nombre del objeto, o vacio si no se
     * intento (historial deshabilitado o sin PAR configurada).
     */
    public String guardarAnalisis(FinancialAnalysisRequestDTO peticion,
                                  FinancialAnalysisResponseDTO respuesta) {
        if (!properties.puedeEscribir()) {
            return "";
        }

        Instant ahora = Instant.now();
        String objeto = "%s/%s/%s-%s.json".formatted(
                properties.prefijo(),
                RUTA_FECHA.format(ahora),
                MARCA_TIEMPO.format(ahora),
                UUID.randomUUID().toString().substring(0, 8));

        byte[] cuerpo;
        try {
            cuerpo = objectMapper.writeValueAsBytes(construirRegistro(ahora, peticion, respuesta));
        } catch (Exception e) {
            log.warn("No se pudo serializar el analisis para archivarlo: {}", e.getMessage());
            return "";
        }

        try {
            ejecutor.submit(() -> subir(objeto, cuerpo));
        } catch (RejectedExecutionException e) {
            log.warn("Cola de archivado saturada; se omite {}", objeto);
            return "";
        }
        return objeto;
    }

    /**
     * Registro que se persiste: perfil, agregados e indicadores.
     *
     * No se guardan las descripciones de las transacciones. Para seguir la
     * evolucion financiera no hacen falta, y almacenarlas convertiria el bucket
     * en un archivo de habitos de consumo identificables.
     */
    private Map<String, Object> construirRegistro(Instant ahora,
                                                  FinancialAnalysisRequestDTO peticion,
                                                  FinancialAnalysisResponseDTO respuesta) {
        Map<String, Object> registro = new LinkedHashMap<>();
        registro.put("timestamp", ahora.toString());
        registro.put("ingreso_mensual", peticion.ingresoMensual());
        registro.put("nivel_endeudamiento", peticion.nivelEndeudamiento());
        registro.put("frecuencia_ahorro", peticion.frecuenciaAhorro());
        registro.put("num_transacciones",
                peticion.transacciones() == null ? 0 : peticion.transacciones().size());
        registro.put("perfil_financiero", respuesta.perfilFinanciero());
        registro.put("probabilidad", respuesta.probabilidad());
        registro.put("resumen_gastos", respuesta.resumenGastos());
        registro.put("factores", respuesta.factores());
        registro.put("modo_degradado", respuesta.modoDegradado());
        return registro;
    }

    private void subir(String objeto, byte[] cuerpo) {
        try {
            restClient.put()
                    .uri(properties.parUrl() + objeto)
                    .header("Content-Type", "application/json")
                    .body(cuerpo)
                    .retrieve()
                    .toBodilessEntity();
            log.debug("Analisis archivado en oci://{}/{}", properties.bucket(), objeto);
        } catch (RestClientException e) {
            // El usuario ya tiene su respuesta; esto solo se registra.
            log.warn("No se pudo archivar {} en Object Storage ({}): {}",
                    objeto, e.getClass().getSimpleName(), e.getMessage());
        }
    }

    @PreDestroy
    void cerrar() {
        ejecutor.shutdown();
        try {
            // Margen para lo que ya esta en vuelo, sin retrasar el apagado.
            if (!ejecutor.awaitTermination(3, TimeUnit.SECONDS)) {
                ejecutor.shutdownNow();
            }
        } catch (InterruptedException e) {
            ejecutor.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }
}
