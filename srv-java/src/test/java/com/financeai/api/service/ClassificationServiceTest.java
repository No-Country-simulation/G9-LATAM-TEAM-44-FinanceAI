package com.financeai.api.service;

import com.financeai.api.config.MlServiceProperties;
import com.financeai.api.dto.TransactionDTO;
import com.financeai.api.integration.FallbackClassifier;
import com.financeai.api.integration.PythonModelClient;
import com.financeai.api.integration.dto.ClasificarResponse;
import com.financeai.api.integration.dto.TopCategoriaMl;
import com.financeai.api.integration.dto.TransaccionClasificadaMl;
import com.financeai.api.integration.dto.TransaccionMl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class ClassificationServiceTest {

    private PythonModelClient modelClient;
    private ClassificationService service;

    @BeforeEach
    void setUp() {
        modelClient = mock(PythonModelClient.class);
        MlServiceProperties properties =
                new MlServiceProperties("http://localhost:8000", true, null, null, 0.5, 0.8);
        service = new ClassificationService(modelClient, new FallbackClassifier(), properties);
    }

    @Test
    @DisplayName("Hace UNA sola llamada por lote, no una por transaccion")
    void llamaUnaVezPorLote() {
        List<TransactionDTO> transacciones = List.of(
                new TransactionDTO("Supermercado", 420.0),
                new TransactionDTO("Gasolina", 300.0),
                new TransactionDTO("Netflix", 40.0));

        when(modelClient.clasificar(anyList())).thenReturn(Optional.of(new ClasificarResponse(List.of(
                new TransaccionClasificadaMl("Supermercado", 420.0, "alimentacion", 0.9, null),
                new TransaccionClasificadaMl("Gasolina", 300.0, "transporte", 0.9, null),
                new TransaccionClasificadaMl("Netflix", 40.0, "ocio", 0.9, null)))));

        ClassificationResult resultado = service.classify(transacciones);

        verify(modelClient, times(1)).clasificar(anyList());
        assertThat(resultado.modoDegradado()).isFalse();
        assertThat(resultado.resumenGastos())
                .containsEntry("alimentacion", 420.0)
                .containsEntry("transporte", 300.0)
                .containsEntry("ocio", 40.0);
    }

    @Test
    @DisplayName("Una categoria por debajo del umbral de confianza degrada a 'otras'")
    void aplicaElUmbralDeConfianza() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.of(new ClasificarResponse(List.of(
                new TransaccionClasificadaMl("Compra rara XYZ", 15.0, "alimentacion", 0.20, null)))));

        ClassificationResult resultado = service.classify(
                List.of(new TransactionDTO("Compra rara XYZ", 15.0)));

        assertThat(resultado.resumenGastos()).containsExactly(
                java.util.Map.entry("otras", 15.0));
    }

    // ------------------------------------------- estado_confianza (Fase 12)

    @Test
    @DisplayName("Confianza >= confianzaAlta (0.8) queda en estado 'aceptado'")
    void confianzaAltaQuedaAceptado() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.of(new ClasificarResponse(List.of(
                new TransaccionClasificadaMl("Supermercado Exito", 420.0, "alimentacion", 0.95, null)))));

        ClassificationResult resultado = service.classify(
                List.of(new TransactionDTO("Supermercado Exito", 420.0)));

        assertThat(resultado.detalle().get(0).estadoConfianza()).isEqualTo("aceptado");
    }

    @Test
    @DisplayName("Confianza entre confianzaMinima y confianzaAlta queda 'requiere_revision'")
    void confianzaMediaQuedaRequiereRevision() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.of(new ClasificarResponse(List.of(
                new TransaccionClasificadaMl("Compra ambigua", 60.0, "ocio", 0.65, null)))));

        ClassificationResult resultado = service.classify(
                List.of(new TransactionDTO("Compra ambigua", 60.0)));

        // La categoria original se conserva: 'estado_confianza' no la reemplaza.
        assertThat(resultado.detalle().get(0).categoria()).isEqualTo("ocio");
        assertThat(resultado.detalle().get(0).estadoConfianza()).isEqualTo("requiere_revision");
    }

    @Test
    @DisplayName("Confianza < confianzaMinima degrada a categoria 'otras' y estado 'otras'")
    void confianzaBajaQuedaEnEstadoOtras() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.of(new ClasificarResponse(List.of(
                new TransaccionClasificadaMl("Compra rara XYZ", 15.0, "alimentacion", 0.20, null)))));

        ClassificationResult resultado = service.classify(
                List.of(new TransactionDTO("Compra rara XYZ", 15.0)));

        assertThat(resultado.detalle().get(0).categoria()).isEqualTo("otras");
        assertThat(resultado.detalle().get(0).estadoConfianza()).isEqualTo("otras");
    }

    @Test
    @DisplayName("En modo degradado, la confianza del respaldo (0.90/0.40) tambien resuelve estado_confianza")
    void estadoConfianzaSeCalculaTambienEnModoDegradado() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.empty());

        ClassificationResult resultado = service.classify(List.of(
                new TransactionDTO("Farmacia San Pablo", 80.0),
                new TransactionDTO("Compra desconocida XYZ", 20.0)));

        assertThat(resultado.modoDegradado()).isTrue();
        // CONFIANZA_KEYWORD=0.90 >= confianzaAlta=0.8
        assertThat(resultado.detalle().get(0).estadoConfianza()).isEqualTo("aceptado");
        // CONFIANZA_SIN_MATCH=0.40 < confianzaMinima=0.5
        assertThat(resultado.detalle().get(1).estadoConfianza()).isEqualTo("otras");
    }

    @Test
    @DisplayName("Si el ml-service no responde, cae al respaldo y marca modo degradado")
    void caeAlRespaldoCuandoNoHayMl() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.empty());

        ClassificationResult resultado = service.classify(List.of(
                new TransactionDTO("Supermercado Exito", 420.0),
                new TransactionDTO("Gasolina Terpel", 300.0)));

        assertThat(resultado.modoDegradado()).isTrue();
        assertThat(resultado.resumenGastos())
                .containsEntry("alimentacion", 420.0)
                .containsEntry("transporte", 300.0);
    }

    @Test
    @DisplayName("Una respuesta con distinta cantidad de items se descarta (no se puede emparejar)")
    void descartaRespuestasIncoherentes() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.of(new ClasificarResponse(List.of(
                new TransaccionClasificadaMl("Supermercado", 420.0, "alimentacion", 0.9, null)))));

        ClassificationResult resultado = service.classify(List.of(
                new TransactionDTO("Supermercado", 420.0),
                new TransactionDTO("Netflix", 40.0)));

        assertThat(resultado.modoDegradado()).isTrue();
        assertThat(resultado.resumenGastos()).containsEntry("ocio", 40.0);
    }

    @Test
    @DisplayName("El monto siempre sale de la transaccion original, no del eco del modelo")
    void confiaEnElMontoDelBackend() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.of(new ClasificarResponse(List.of(
                // el modelo devuelve un valor manipulado: debe ignorarse
                new TransaccionClasificadaMl("Supermercado", 999999.0, "alimentacion", 0.9, null)))));

        ClassificationResult resultado = service.classify(
                List.of(new TransactionDTO("Supermercado", 420.0)));

        assertThat(resultado.resumenGastos()).containsEntry("alimentacion", 420.0);
    }

    @Test
    @DisplayName("Una categoria desconocida del modelo degrada a 'otras' sin reventar")
    void categoriaDesconocidaDegrada() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.of(new ClasificarResponse(List.of(
                new TransaccionClasificadaMl("Algo", 50.0, "criptomonedas", 0.95, null)))));

        ClassificationResult resultado = service.classify(
                List.of(new TransactionDTO("Algo", 50.0)));

        assertThat(resultado.resumenGastos()).containsEntry("otras", 50.0);
    }

    @Test
    @DisplayName("El respaldo local usa las mismas keywords que reglas.py en srv-python")
    void respaldoEspejaLasKeywordsDePython() {
        FallbackClassifier fallback = new FallbackClassifier();

        assertThat(fallback.clasificar("Rappi Comida").getValor()).isEqualTo("alimentacion");
        assertThat(fallback.clasificar("Recarga Tarjeta Metro").getValor()).isEqualTo("transporte");
        assertThat(fallback.clasificar("Drogueria Cruz Verde").getValor()).isEqualTo("salud");
        assertThat(fallback.clasificar("Arriendo Mensual").getValor()).isEqualTo("vivienda");
        assertThat(fallback.clasificar("Curso Udemy Online").getValor()).isEqualTo("educacion");
        assertThat(fallback.clasificar("Spotify Premium").getValor()).isEqualTo("ocio");
        assertThat(fallback.clasificar("Movistar Internet Hogar").getValor()).isEqualTo("servicios");
        assertThat(fallback.clasificar("Compra desconocida XYZ").getValor()).isEqualTo("otras");
        assertThat(fallback.clasificar(null).getValor()).isEqualTo("otras");
    }

    @Test
    @DisplayName("Envia al modelo exactamente las transacciones recibidas")
    void mapeaLasTransaccionesAlContrato() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.empty());

        service.classify(List.of(
                new TransactionDTO("Supermercado", 420.0),
                new TransactionDTO("Netflix", 40.0)));

        ArgumentCaptor<List<TransaccionMl>> captor = ArgumentCaptor.captor();
        verify(modelClient).clasificar(captor.capture());

        assertThat(captor.getValue()).containsExactly(
                new TransaccionMl("Supermercado", 420.0),
                new TransaccionMl("Netflix", 40.0));
    }

    @Test
    @DisplayName("Sin transacciones no se llama al ml-service ni se marca degradado")
    void listaVaciaNoLlamaAlModelo() {
        ClassificationResult resultado = service.classify(List.of());

        verify(modelClient, never()).clasificar(anyList());
        assertThat(resultado.detalle()).isEmpty();
        assertThat(resultado.resumenGastos()).isEmpty();
        assertThat(resultado.modoDegradado()).isFalse();
    }

    @Test
    @DisplayName("El detalle conserva el orden y la descripcion original de la peticion")
    void elDetalleRespetaLaEntrada() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.of(new ClasificarResponse(List.of(
                new TransaccionClasificadaMl("eco distinto", 1.0, "alimentacion", 0.95, null),
                new TransaccionClasificadaMl("otro eco", 2.0, "transporte", 0.88, null)))));

        ClassificationResult resultado = service.classify(List.of(
                new TransactionDTO("Supermercado Exito", 420.0),
                new TransactionDTO("Gasolinera Terpel", 300.0)));

        assertThat(resultado.detalle()).hasSize(2);
        // Descripcion y monto salen de la peticion, no del eco del modelo.
        assertThat(resultado.detalle().get(0).descripcion()).isEqualTo("Supermercado Exito");
        assertThat(resultado.detalle().get(0).valor()).isEqualTo(420.0);
        assertThat(resultado.detalle().get(0).categoria()).isEqualTo("alimentacion");
        assertThat(resultado.detalle().get(1).categoria()).isEqualTo("transporte");
    }

    @Test
    @DisplayName("En modo degradado el detalle tambien viene completo y con confianza declarada")
    void elDetalleExisteTambienDegradado() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.empty());

        ClassificationResult resultado = service.classify(List.of(
                new TransactionDTO("Farmacia San Pablo", 80.0),
                new TransactionDTO("Compra desconocida XYZ", 20.0)));

        assertThat(resultado.modoDegradado()).isTrue();
        assertThat(resultado.detalle()).hasSize(2);
        assertThat(resultado.detalle().get(0).categoria()).isEqualTo("salud");
        assertThat(resultado.detalle().get(0).confianza())
                .isEqualTo(FallbackClassifier.CONFIANZA_KEYWORD);
        assertThat(resultado.detalle().get(1).categoria()).isEqualTo("otras");
        assertThat(resultado.detalle().get(1).confianza())
                .isEqualTo(FallbackClassifier.CONFIANZA_SIN_MATCH);
    }

    @Test
    @DisplayName("El total de gastos coincide con la suma del resumen")
    void elTotalCuadraConElResumen() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.empty());

        ClassificationResult resultado = service.classify(List.of(
                new TransactionDTO("Supermercado Exito", 420.0),
                new TransactionDTO("Gasolinera Terpel", 300.0),
                new TransactionDTO("Netflix", 40.0)));

        assertThat(resultado.totalGastos()).isEqualTo(760.0);
    }

    // ------------------------------------------------------------- top3 (Fase 16)

    @Test
    @DisplayName("top3 se traduce del ml-service manteniendo el orden descendente")
    void top3SeTraduceDelModeloEnOrden() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.of(new ClasificarResponse(List.of(
                new TransaccionClasificadaMl("Supermercado Exito", 420.0, "alimentacion", 0.95, null,
                        List.of(
                                new TopCategoriaMl("alimentacion", 0.95),
                                new TopCategoriaMl("otras", 0.03),
                                new TopCategoriaMl("ocio", 0.02)))))));

        ClassificationResult resultado = service.classify(
                List.of(new TransactionDTO("Supermercado Exito", 420.0)));

        List<com.financeai.api.dto.TopCategoryDTO> top3 = resultado.detalle().get(0).top3();
        assertThat(top3).hasSize(3);
        assertThat(top3.get(0).categoria()).isEqualTo("alimentacion");
        assertThat(top3.get(0).confianza()).isEqualTo(0.95);
        assertThat(top3.get(1).categoria()).isEqualTo("otras");
        assertThat(top3.get(2).categoria()).isEqualTo("ocio");
    }

    @Test
    @DisplayName("top3 nunca tiene mas de 3 elementos aunque el ml-service mande mas")
    void top3RespetaElLimiteDeTres() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.of(new ClasificarResponse(List.of(
                new TransaccionClasificadaMl("Compra", 10.0, "alimentacion", 0.5, null,
                        List.of(
                                new TopCategoriaMl("alimentacion", 0.5),
                                new TopCategoriaMl("otras", 0.3),
                                new TopCategoriaMl("ocio", 0.1),
                                new TopCategoriaMl("salud", 0.1)))))));

        ClassificationResult resultado = service.classify(
                List.of(new TransactionDTO("Compra", 10.0)));

        assertThat(resultado.detalle().get(0).top3()).hasSizeLessThanOrEqualTo(3);
    }

    @Test
    @DisplayName("Si el ml-service no manda top3 (contrato anterior a la Fase 16), no revienta")
    void top3AusenteEnLaRespuestaDelModeloNoRevienta() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.of(new ClasificarResponse(List.of(
                new TransaccionClasificadaMl("Supermercado", 420.0, "alimentacion", 0.9, null)))));

        ClassificationResult resultado = service.classify(
                List.of(new TransactionDTO("Supermercado", 420.0)));

        assertThat(resultado.detalle().get(0).top3()).isEmpty();
    }

    @Test
    @DisplayName("En modo degradado, top3 trae un solo elemento con la categoria del respaldo")
    void top3EnModoDegradadoTieneUnSoloElemento() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.empty());

        ClassificationResult resultado = service.classify(List.of(
                new TransactionDTO("Farmacia San Pablo", 80.0),
                new TransactionDTO("Compra desconocida XYZ", 20.0)));

        assertThat(resultado.detalle().get(0).top3()).hasSize(1);
        assertThat(resultado.detalle().get(0).top3().get(0).categoria()).isEqualTo("salud");
        assertThat(resultado.detalle().get(1).top3()).hasSize(1);
        assertThat(resultado.detalle().get(1).top3().get(0).categoria()).isEqualTo("otras");
    }

    @Test
    @DisplayName("top3 siempre incluye la categoria principal como primer elemento")
    void top3IncluyeLaCategoriaPrincipalPrimero() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.of(new ClasificarResponse(List.of(
                new TransaccionClasificadaMl("Netflix", 40.0, "ocio", 0.88, null,
                        List.of(new TopCategoriaMl("ocio", 0.88), new TopCategoriaMl("otras", 0.05)))))));

        ClassificationResult resultado = service.classify(
                List.of(new TransactionDTO("Netflix", 40.0)));

        var detalle = resultado.detalle().get(0);
        assertThat(detalle.top3().get(0).categoria()).isEqualTo(detalle.categoria());
    }
}
