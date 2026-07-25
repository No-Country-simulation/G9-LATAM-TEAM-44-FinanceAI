package com.financeai.api.service;

import com.financeai.api.config.MlServiceProperties;
import com.financeai.api.dto.TransactionDTO;
import com.financeai.api.integration.FallbackClassifier;
import com.financeai.api.integration.PythonModelClient;
import com.financeai.api.integration.dto.ClasificarResponse;
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
                new MlServiceProperties("http://localhost:8000", true, null, null, 0.5);
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
                new TransaccionClasificadaMl("Supermercado", 420.0, "alimentacion", 0.9),
                new TransaccionClasificadaMl("Gasolina", 300.0, "transporte", 0.9),
                new TransaccionClasificadaMl("Netflix", 40.0, "ocio", 0.9)))));

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
                new TransaccionClasificadaMl("Compra rara XYZ", 15.0, "alimentacion", 0.20)))));

        ClassificationResult resultado = service.classify(
                List.of(new TransactionDTO("Compra rara XYZ", 15.0)));

        assertThat(resultado.resumenGastos()).containsExactly(
                java.util.Map.entry("otras", 15.0));
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
                new TransaccionClasificadaMl("Supermercado", 420.0, "alimentacion", 0.9)))));

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
                new TransaccionClasificadaMl("Supermercado", 999999.0, "alimentacion", 0.9)))));

        ClassificationResult resultado = service.classify(
                List.of(new TransactionDTO("Supermercado", 420.0)));

        assertThat(resultado.resumenGastos()).containsEntry("alimentacion", 420.0);
    }

    @Test
    @DisplayName("Una categoria desconocida del modelo degrada a 'otras' sin reventar")
    void categoriaDesconocidaDegrada() {
        when(modelClient.clasificar(anyList())).thenReturn(Optional.of(new ClasificarResponse(List.of(
                new TransaccionClasificadaMl("Algo", 50.0, "criptomonedas", 0.95)))));

        ClassificationResult resultado = service.classify(
                List.of(new TransactionDTO("Algo", 50.0)));

        assertThat(resultado.resumenGastos()).containsEntry("otras", 50.0);
    }

    @Test
    @DisplayName("El respaldo local usa las mismas keywords que el stub de Python")
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
        assertThat(resultado.resumenGastos()).isEmpty();
        assertThat(resultado.modoDegradado()).isFalse();
    }
}
