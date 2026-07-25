package com.financeai.api.integration;

import com.financeai.api.config.MlServiceProperties;
import com.financeai.api.integration.dto.ClasificarResponse;
import com.financeai.api.integration.dto.PerfilRequest;
import com.financeai.api.integration.dto.PerfilResponse;
import com.financeai.api.integration.dto.TransaccionMl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.jsonPath;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withServerError;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

/**
 * Verifica el contrato HTTP con srv-python sin levantar Python.
 *
 * Lo importante aqui es que el JSON que sale y entra sea EXACTAMENTE el que
 * define app/main.py (snake_case), y que un fallo del servicio no propague
 * excepciones hacia arriba.
 */
class PythonModelClientTest {

    private RestClient.Builder builder;
    private MockRestServiceServer server;
    private PythonModelClient client;

    @BeforeEach
    void setUp() {
        builder = RestClient.builder().baseUrl("http://ml-service:8000");
        server = MockRestServiceServer.bindTo(builder).build();
        MlServiceProperties properties =
                new MlServiceProperties("http://ml-service:8000", true, null, null, 0.5);
        client = new PythonModelClient(builder.build(), properties);
    }

    @Test
    @DisplayName("/clasificar envia snake_case y deserializa transacciones_clasificadas")
    void clasificarRespetaElContrato() {
        server.expect(requestTo("http://ml-service:8000/clasificar"))
                .andExpect(method(org.springframework.http.HttpMethod.POST))
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.transacciones[0].descripcion").value("Supermercado"))
                .andExpect(jsonPath("$.transacciones[0].valor").value(420.0))
                .andRespond(withSuccess("""
                        {"transacciones_clasificadas":[
                          {"descripcion":"Supermercado","valor":420,
                           "categoria":"alimentacion","confianza":0.9}
                        ]}
                        """, MediaType.APPLICATION_JSON));

        Optional<ClasificarResponse> respuesta =
                client.clasificar(List.of(new TransaccionMl("Supermercado", 420.0)));

        assertThat(respuesta).isPresent();
        assertThat(respuesta.get().transaccionesClasificadas()).hasSize(1);
        assertThat(respuesta.get().transaccionesClasificadas().get(0).categoria())
                .isEqualTo("alimentacion");
        assertThat(respuesta.get().transaccionesClasificadas().get(0).confianza())
                .isEqualTo(0.9);
        server.verify();
    }

    @Test
    @DisplayName("/perfil envia los agregados en snake_case y lee los factores")
    void perfilRespetaElContrato() {
        server.expect(requestTo("http://ml-service:8000/perfil"))
                .andExpect(method(org.springframework.http.HttpMethod.POST))
                .andExpect(jsonPath("$.ingreso_mensual").value(4500.0))
                .andExpect(jsonPath("$.nivel_endeudamiento").value(25))
                .andExpect(jsonPath("$.frecuencia_ahorro").value("Media"))
                .andExpect(jsonPath("$.resumen_gastos.alimentacion").value(420.0))
                .andRespond(withSuccess("""
                        {"perfil_financiero":"Saludable","probabilidad":0.9,
                         "factores":[{"nombre":"tasa_gasto","valor":0.16,"impacto":"baja_riesgo"}]}
                        """, MediaType.APPLICATION_JSON));

        Optional<PerfilResponse> respuesta = client.perfil(new PerfilRequest(
                4500.0, 25, "Media", Map.of("alimentacion", 420.0)));

        assertThat(respuesta).isPresent();
        assertThat(respuesta.get().perfilFinanciero()).isEqualTo("Saludable");
        assertThat(respuesta.get().probabilidad()).isEqualTo(0.9);
        assertThat(respuesta.get().factores()).hasSize(1);
        assertThat(respuesta.get().factores().get(0).impacto()).isEqualTo("baja_riesgo");
        server.verify();
    }

    @Test
    @DisplayName("Si el ml-service falla, devuelve empty en vez de propagar la excepcion")
    void erroresDelServicioNoSePropagan() {
        server.expect(requestTo("http://ml-service:8000/clasificar"))
                .andRespond(withServerError());

        Optional<ClasificarResponse> respuesta =
                client.clasificar(List.of(new TransaccionMl("Supermercado", 420.0)));

        assertThat(respuesta).isEmpty();
    }

    @Test
    @DisplayName("Un 422 de validacion de Python tampoco tumba la peticion")
    void erroresDeValidacionNoSePropagan() {
        server.expect(requestTo("http://ml-service:8000/perfil"))
                .andRespond(withStatus(HttpStatus.UNPROCESSABLE_ENTITY));

        Optional<PerfilResponse> respuesta = client.perfil(new PerfilRequest(
                4500.0, 25, "Siempre", Map.of("ocio", 10.0)));

        assertThat(respuesta).isEmpty();
    }

    @Test
    @DisplayName("Con ml.service.enabled=false ni siquiera intenta la llamada")
    void deshabilitadoNoLlama() {
        MlServiceProperties apagado =
                new MlServiceProperties("http://ml-service:8000", false, null, null, 0.5);
        PythonModelClient sinMl = new PythonModelClient(builder.build(), apagado);

        assertThat(sinMl.clasificar(List.of(new TransaccionMl("Supermercado", 420.0)))).isEmpty();
        assertThat(sinMl.disponible()).isFalse();
        server.verify(); // no se esperaba ninguna peticion
    }
}
