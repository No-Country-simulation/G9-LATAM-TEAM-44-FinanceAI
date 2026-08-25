package com.financeai.api.integration;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.financeai.api.config.OciProperties;
import com.financeai.api.dto.ClassifiedTransactionDTO;
import com.financeai.api.dto.FactorDTO;
import com.financeai.api.dto.FinancialAnalysisRequestDTO;
import com.financeai.api.dto.FinancialAnalysisResponseDTO;
import com.financeai.api.dto.TransactionDTO;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class OCIStorageServiceTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    private OCIStorageService servicio(String parUrl, boolean historial) {
        return new OCIStorageService(
                new OciProperties(parUrl, "finance-ai-models", "ns", "us-ashburn-1", "historial", historial),
                objectMapper);
    }

    private FinancialAnalysisRequestDTO peticion() {
        return new FinancialAnalysisRequestDTO(4500.0, 25, "Media",
                List.of(new TransactionDTO("Supermercado Exito", 420.0)));
    }

    private FinancialAnalysisResponseDTO respuesta() {
        return new FinancialAnalysisResponseDTO("Saludable", 0.9,
                Map.of("alimentacion", 420.0), List.of("Todo bien"),
                List.of(new FactorDTO("tasa_gasto", 0.09, "baja_riesgo")), List.of(), false);
    }

    @Test
    @DisplayName("Sin PAR configurada no se intenta archivar nada")
    void sinParNoArchiva() {
        assertThat(servicio(null, true).guardarAnalisis(peticion(), respuesta())).isEmpty();
        assertThat(servicio("", true).guardarAnalisis(peticion(), respuesta())).isEmpty();
    }

    @Test
    @DisplayName("Con el historial deshabilitado no se archiva aunque haya PAR")
    void historialDeshabilitadoNoArchiva() {
        OCIStorageService servicio = servicio("https://objectstorage.example.com/p/abc/n/ns/b/bucket/o/", false);
        assertThat(servicio.guardarAnalisis(peticion(), respuesta())).isEmpty();
    }

    @Test
    @DisplayName("El objeto se nombra con jerarquia por fecha, que es como se podra consultar despues")
    void elNombreDelObjetoSeParticionaPorFecha() {
        OCIStorageService servicio = servicio("https://objectstorage.example.com/p/abc/n/ns/b/bucket/o/", true);

        String objeto = servicio.guardarAnalisis(peticion(), respuesta());

        // historial/AAAA/MM/DD/AAAAMMDDTHHMMSS-xxxxxxxx.json
        assertThat(objeto).matches("historial/\\d{4}/\\d{2}/\\d{2}/\\d{8}T\\d{6}-[0-9a-f]{8}\\.json");
    }

    @Test
    @DisplayName("Las descripciones de las transacciones no salen hacia Object Storage")
    void elArchivadoNoLlevaDescripciones() {
        List<ClassifiedTransactionDTO> detalle = List.of(new ClassifiedTransactionDTO(
                "Farmacia San Pablo", 130.0, "salud", 0.99, "aceptado", List.of()));
        FinancialAnalysisResponseDTO conDetalle = new FinancialAnalysisResponseDTO(
                "Saludable", 0.9, Map.of("salud", 130.0), List.of("Todo bien"),
                List.of(new FactorDTO("tasa_gasto", 0.09, "baja_riesgo")), detalle, false);

        // La respuesta lleva descripciones desde que el frontend abre cada
        // categoria; el registro que se archiva no debe heredarlas.
        Map<String, Object> registro = servicio("https://x/o/", true)
                .construirRegistro(Instant.now(), peticion(), conDetalle);

        assertThat(registro).doesNotContainKey("transacciones_clasificadas");
        assertThat(registro.toString()).doesNotContain("Farmacia San Pablo");
    }

    @Test
    @DisplayName("Un fallo de red al archivar no se propaga al usuario")
    void unFalloDeRedNoRompeElAnalisis() {
        // Puerto cerrado: la subida falla en el hilo de fondo.
        OCIStorageService servicio = servicio("http://127.0.0.1:1/o/", true);

        assertThat(servicio.guardarAnalisis(peticion(), respuesta())).isNotEmpty();
    }

    @Test
    @DisplayName("La PAR sin barra final se normaliza")
    void normalizaLaBarraFinal() {
        OciProperties propiedades = new OciProperties(
                "https://objectstorage.example.com/p/abc/n/ns/b/bucket/o", null, null, null, null, null);

        assertThat(propiedades.parUrl()).endsWith("/");
        assertThat(propiedades.puedeEscribir()).isTrue();
    }

    @Test
    @DisplayName("El estado declara el bucket y si el historial esta activo")
    void reportaSuEstado() {
        Map<String, Object> estado =
                servicio("https://objectstorage.example.com/p/abc/n/ns/b/bucket/o/", true).estado();

        assertThat(estado).containsEntry("bucket", "finance-ai-models");
        assertThat(estado).containsEntry("historial_habilitado", true);
        assertThat(estado.get("modelo").toString()).startsWith("oci://finance-ai-models/");
    }
}
