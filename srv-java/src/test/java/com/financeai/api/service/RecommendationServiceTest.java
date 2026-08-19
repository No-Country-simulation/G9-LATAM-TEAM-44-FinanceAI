package com.financeai.api.service;

import com.financeai.api.dto.FinancialAnalysisRequestDTO;
import com.financeai.api.dto.TransactionDTO;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class RecommendationServiceTest {

    private final RecommendationService service = new RecommendationService();

    private FinancialAnalysisRequestDTO peticion(double ingreso, int deuda, String ahorro) {
        return new FinancialAnalysisRequestDTO(ingreso, deuda, ahorro,
                List.of(new TransactionDTO("Compra", 10.0)));
    }

    @Test
    @DisplayName("Gastar mas que el ingreso es siempre la primera recomendacion")
    void elSobregastoVaPrimero() {
        List<String> recomendaciones = service.generateRecommendations(
                peticion(2000, 20, "Media"),
                Map.of("vivienda", 1500.0, "alimentacion", 900.0));

        assertThat(recomendaciones.get(0)).contains("superan tu ingreso mensual");
    }

    @Test
    @DisplayName("Un endeudamiento alto genera su propia recomendacion")
    void avisaDeLaDeudaAlta() {
        List<String> recomendaciones = service.generateRecommendations(
                peticion(4000, 55, "Media"), Map.of("vivienda", 1000.0));

        assertThat(recomendaciones).anyMatch(r -> r.contains("endeudamiento"));
    }

    @Test
    @DisplayName("Ahorrar poco o nada dispara el consejo de automatizar el ahorro")
    void sugiereAutomatizarElAhorro() {
        for (String frecuencia : List.of("Baja", "Nula", "baja", "NULA")) {
            List<String> recomendaciones = service.generateRecommendations(
                    peticion(4000, 10, frecuencia), Map.of("vivienda", 1000.0));

            assertThat(recomendaciones)
                    .as("frecuencia %s", frecuencia)
                    .anyMatch(r -> r.contains("Automatiza un ahorro"));
        }
    }

    @Test
    @DisplayName("Ahorrar con frecuencia alta o media no dispara ese consejo")
    void noInsisteAQuienYaAhorra() {
        List<String> recomendaciones = service.generateRecommendations(
                peticion(4000, 10, "Alta"), Map.of("vivienda", 1000.0));

        assertThat(recomendaciones).noneMatch(r -> r.contains("Automatiza un ahorro"));
    }

    @Test
    @DisplayName("Una categoria muy por encima del patron saludable se senala con su magnitud")
    void senalaLaCategoriaDesviada() {
        // ocio = 50% del gasto, muy por encima del 7,8% de un perfil saludable.
        List<String> recomendaciones = service.generateRecommendations(
                peticion(4000, 10, "Alta"),
                Map.of("ocio", 1000.0, "vivienda", 1000.0));

        assertThat(recomendaciones).anyMatch(r -> r.contains("ocio") && r.contains("veces"));
    }

    @Test
    @DisplayName("Una categoria desviada pero irrelevante en monto no se menciona")
    void ignoraLasDesviacionesSinImpacto() {
        // ocio esta al triple del patron, pero es el 3% del gasto: recortarlo no
        // cambia nada y mencionarlo solo distraeria de lo importante.
        List<String> recomendaciones = service.generateRecommendations(
                peticion(10000, 5, "Alta"),
                Map.of("ocio", 30.0, "vivienda", 970.0));

        assertThat(recomendaciones).noneMatch(r -> r.contains("ocio"));
    }

    @Test
    @DisplayName("Sin problemas detectados devuelve un mensaje de refuerzo, nunca lista vacia")
    void siempreDevuelveAlgo() {
        List<String> recomendaciones = service.generateRecommendations(
                peticion(10000, 5, "Alta"), Map.of("vivienda", 1000.0));

        assertThat(recomendaciones).hasSize(1);
        assertThat(recomendaciones.get(0)).contains("rango saludable");
    }

    @Test
    @DisplayName("Nunca se devuelven mas de cuatro recomendaciones")
    void limitaLaCantidad() {
        // Situacion critica en todos los frentes a la vez.
        List<String> recomendaciones = service.generateRecommendations(
                peticion(1000, 80, "Nula"),
                Map.of("ocio", 600.0, "otras", 400.0, "transporte", 300.0, "servicios", 200.0));

        assertThat(recomendaciones).hasSizeLessThanOrEqualTo(4);
    }

    @Test
    @DisplayName("Un resumen de gastos vacio no rompe el motor")
    void toleraGastosVacios() {
        List<String> recomendaciones = service.generateRecommendations(
                peticion(3000, 10, "Alta"), Map.of());

        assertThat(recomendaciones).isNotEmpty();
    }
}
