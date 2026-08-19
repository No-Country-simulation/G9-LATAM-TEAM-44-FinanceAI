package com.financeai.api.service;

import com.financeai.api.dto.FinancialAnalysisRequestDTO;
import com.financeai.api.dto.TransactionDTO;
import com.financeai.api.integration.PythonModelClient;
import com.financeai.api.integration.dto.FactorMl;
import com.financeai.api.integration.dto.PerfilResponse;
import com.financeai.api.model.FinancialProfile;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class ProfileServiceTest {

    private PythonModelClient modelClient;
    private ProfileService service;

    @BeforeEach
    void setUp() {
        modelClient = mock(PythonModelClient.class);
        service = new ProfileService(modelClient);
    }

    private FinancialAnalysisRequestDTO peticion(double ingreso, int deuda, String ahorro) {
        return new FinancialAnalysisRequestDTO(ingreso, deuda, ahorro,
                List.of(new TransactionDTO("Compra", 10.0)));
    }

    private PerfilResponse respuestaMl(String perfil, Double probabilidad) {
        return new PerfilResponse(perfil, probabilidad,
                List.of(new FactorMl("tasa_gasto", 0.5, "baja_riesgo")));
    }

    @Test
    @DisplayName("Usa el perfil del modelo cuando la respuesta es válida")
    void confiaEnElModelo() {
        when(modelClient.perfil(any())).thenReturn(
                Optional.of(respuestaMl("En riesgo", 0.93)));

        ProfileResult resultado = service.evaluar(peticion(3000, 20, "Alta"), Map.of("ocio", 100.0));

        assertThat(resultado.perfilFinanciero()).isEqualTo("En riesgo");
        assertThat(resultado.probabilidad()).isEqualTo(0.93);
        assertThat(resultado.modoDegradado()).isFalse();
    }

    @Test
    @DisplayName("Normaliza la etiqueta sin tilde a la forma canónica")
    void normalizaLaTilde() {
        when(modelClient.perfil(any())).thenReturn(
                Optional.of(respuestaMl("En observacion", 0.7)));

        ProfileResult resultado = service.evaluar(peticion(3000, 20, "Alta"), Map.of("ocio", 100.0));

        assertThat(resultado.perfilFinanciero()).isEqualTo("En observación");
    }

    @Test
    @DisplayName("Un perfil fuera del contrato se descarta y se usan los umbrales locales")
    void descartaPerfilesDesconocidos() {
        when(modelClient.perfil(any())).thenReturn(
                Optional.of(respuestaMl("Excelente", 0.99)));

        ProfileResult resultado = service.evaluar(peticion(5000, 10, "Alta"), Map.of("ocio", 500.0));

        assertThat(resultado.modoDegradado()).isTrue();
        assertThat(resultado.perfilFinanciero()).isEqualTo("Saludable");
    }

    @Test
    @DisplayName("Una probabilidad fuera de [0,1] invalida la respuesta del modelo")
    void descartaProbabilidadesImposibles() {
        when(modelClient.perfil(any())).thenReturn(
                Optional.of(respuestaMl("En riesgo", 1.4)));

        ProfileResult resultado = service.evaluar(peticion(5000, 10, "Alta"), Map.of("ocio", 500.0));

        assertThat(resultado.modoDegradado()).isTrue();
    }

    @Test
    @DisplayName("Sin ml-service, los umbrales locales cubren los tres perfiles")
    void umbralesLocales() {
        when(modelClient.perfil(any())).thenReturn(Optional.empty());

        ProfileResult sano = service.evaluar(peticion(5000, 10, "Alta"), Map.of("vivienda", 1000.0));
        ProfileResult observado = service.evaluar(peticion(5000, 35, "Media"), Map.of("vivienda", 1000.0));
        ProfileResult riesgo = service.evaluar(peticion(1000, 10, "Nula"), Map.of("vivienda", 1500.0));

        assertThat(sano.perfilFinanciero()).isEqualTo(FinancialProfile.SALUDABLE.getValor());
        assertThat(observado.perfilFinanciero()).isEqualTo(FinancialProfile.EN_OBSERVACION.getValor());
        assertThat(riesgo.perfilFinanciero()).isEqualTo(FinancialProfile.EN_RIESGO.getValor());
        assertThat(sano.modoDegradado()).isTrue();
    }

    @Test
    @DisplayName("El respaldo local siempre devuelve tres factores explicativos")
    void elRespaldoExplicaSuDecision() {
        when(modelClient.perfil(any())).thenReturn(Optional.empty());

        ProfileResult resultado = service.evaluar(peticion(3000, 60, "Nula"), Map.of("ocio", 2000.0));

        assertThat(resultado.factores()).hasSize(3);
        assertThat(resultado.factores()).allSatisfy(f ->
                assertThat(f.impacto()).isIn("sube_riesgo", "baja_riesgo"));
    }

    @Test
    @DisplayName("FinancialProfile acepta cualquier capitalización y rechaza lo desconocido")
    void elEnumNormaliza() {
        assertThat(FinancialProfile.desdeValor("EN OBSERVACIÓN")).isEqualTo(FinancialProfile.EN_OBSERVACION);
        assertThat(FinancialProfile.desdeValor("en observacion")).isEqualTo(FinancialProfile.EN_OBSERVACION);
        assertThat(FinancialProfile.desdeValor("  Saludable  ")).isEqualTo(FinancialProfile.SALUDABLE);
        assertThat(FinancialProfile.desdeValor("Excelente")).isNull();
        assertThat(FinancialProfile.desdeValor(null)).isNull();
        assertThat(FinancialProfile.esValido("En riesgo")).isTrue();
    }
}
