package com.financeai.api.controller;

import com.financeai.api.dto.ClassifiedTransactionDTO;
import com.financeai.api.dto.FactorDTO;
import com.financeai.api.dto.FinancialAnalysisResponseDTO;
import com.financeai.api.integration.OCIStorageService;
import com.financeai.api.integration.PythonModelClient;
import com.financeai.api.service.ClassificationResult;
import com.financeai.api.service.ClassificationService;
import com.financeai.api.service.FinancialAnalysisService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(FinancialController.class)
class FinancialControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private FinancialAnalysisService analysisService;

    @MockitoBean
    private ClassificationService classificationService;

    @MockitoBean
    private PythonModelClient modelClient;

    @MockitoBean
    private OCIStorageService ociStorageService;

    private static final String PETICION_VALIDA = """
            {
              "ingreso_mensual": 4500,
              "nivel_endeudamiento": 25,
              "frecuencia_ahorro": "Media",
              "transacciones": [
                {"descripcion": "Supermercado", "valor": 420},
                {"descripcion": "Gasolina", "valor": 300}
              ]
            }
            """;

    @Test
    @DisplayName("Delega en el servicio y responde en snake_case (ya no es un mock estatico)")
    void delegaEnElServicio() throws Exception {
        when(analysisService.analyze(any())).thenReturn(new FinancialAnalysisResponseDTO(
                "Saludable",
                0.90,
                Map.of("alimentacion", 420.0, "transporte", 300.0),
                List.of("Mantener el control de gastos."),
                List.of(new FactorDTO("tasa_gasto", 0.16, "baja_riesgo")),
                false));

        mockMvc.perform(post("/api/v1/analisis-financiero")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(PETICION_VALIDA))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.perfil_financiero").value("Saludable"))
                .andExpect(jsonPath("$.probabilidad").value(0.90))
                .andExpect(jsonPath("$.resumen_gastos.alimentacion").value(420.0))
                .andExpect(jsonPath("$.recomendaciones").isArray())
                .andExpect(jsonPath("$.factores[0].nombre").value("tasa_gasto"))
                .andExpect(jsonPath("$.factores[0].impacto").value("baja_riesgo"))
                .andExpect(jsonPath("$.modo_degradado").value(false));

        verify(analysisService).analyze(any());
    }

    @Test
    @DisplayName("Un ingreso en 0 se rechaza con 400 antes de llegar a Python (alli seria 422)")
    void rechazaIngresoCero() throws Exception {
        String peticion = PETICION_VALIDA.replace("\"ingreso_mensual\": 4500", "\"ingreso_mensual\": 0");

        mockMvc.perform(post("/api/v1/analisis-financiero")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(peticion))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.codigo_estado").value(400))
                .andExpect(jsonPath("$.detalles.ingresoMensual").exists());

        verify(analysisService, never()).analyze(any());
    }

    @Test
    @DisplayName("Un endeudamiento mayor a 100 se rechaza con 400")
    void rechazaEndeudamientoFueraDeRango() throws Exception {
        String peticion = PETICION_VALIDA.replace("\"nivel_endeudamiento\": 25", "\"nivel_endeudamiento\": 150");

        mockMvc.perform(post("/api/v1/analisis-financiero")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(peticion))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detalles.nivelEndeudamiento").exists());

        verify(analysisService, never()).analyze(any());
    }

    @Test
    @DisplayName("Una frecuencia de ahorro fuera del enum se rechaza con 400")
    void rechazaFrecuenciaInvalida() throws Exception {
        String peticion = PETICION_VALIDA.replace("\"frecuencia_ahorro\": \"Media\"",
                "\"frecuencia_ahorro\": \"Siempre\"");

        mockMvc.perform(post("/api/v1/analisis-financiero")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(peticion))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detalles.frecuenciaAhorro").exists());

        verify(analysisService, never()).analyze(any());
    }

    @Test
    @DisplayName("Una lista de transacciones vacia se rechaza con 400")
    void rechazaTransaccionesVacias() throws Exception {
        String peticion = """
                {
                  "ingreso_mensual": 4500,
                  "nivel_endeudamiento": 25,
                  "frecuencia_ahorro": "Media",
                  "transacciones": []
                }
                """;

        mockMvc.perform(post("/api/v1/analisis-financiero")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(peticion))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detalles.transacciones").exists());

        verify(analysisService, never()).analyze(any());
    }

    // ------------------------------------------------ /clasificar-transacciones

    @Test
    @DisplayName("Clasificar devuelve el detalle por transaccion y el agregado por categoria")
    void clasificaTransacciones() throws Exception {
        when(classificationService.classify(any())).thenReturn(new ClassificationResult(
                List.of(
                        new ClassifiedTransactionDTO("Supermercado Exito", 420.0, "alimentacion", 0.99, "aceptado"),
                        new ClassifiedTransactionDTO("Gasolinera Terpel", 300.0, "transporte", 0.97, "aceptado")),
                Map.of("alimentacion", 420.0, "transporte", 300.0),
                false));

        String peticion = """
                {
                  "transacciones": [
                    {"descripcion": "Supermercado Exito", "valor": 420},
                    {"descripcion": "Gasolinera Terpel", "valor": 300}
                  ]
                }
                """;

        mockMvc.perform(post("/api/v1/clasificar-transacciones")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(peticion))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.transacciones_clasificadas[0].categoria").value("alimentacion"))
                .andExpect(jsonPath("$.transacciones_clasificadas[0].confianza").value(0.99))
                .andExpect(jsonPath("$.transacciones_clasificadas[1].categoria").value("transporte"))
                .andExpect(jsonPath("$.resumen_gastos.alimentacion").value(420.0))
                .andExpect(jsonPath("$.total_gastos").value(720.0))
                .andExpect(jsonPath("$.modo_degradado").value(false));
    }

    @Test
    @DisplayName("Clasificar no exige ingreso ni endeudamiento: no los necesita")
    void clasificarNoPideDatosFinancieros() throws Exception {
        when(classificationService.classify(any())).thenReturn(new ClassificationResult(
                List.of(new ClassifiedTransactionDTO("Netflix", 40.0, "ocio", 0.95, "aceptado")),
                Map.of("ocio", 40.0),
                false));

        mockMvc.perform(post("/api/v1/clasificar-transacciones")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"transacciones\":[{\"descripcion\":\"Netflix\",\"valor\":40}]}"))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("Clasificar rechaza una lista vacia con 400")
    void clasificarRechazaListaVacia() throws Exception {
        mockMvc.perform(post("/api/v1/clasificar-transacciones")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"transacciones\": []}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detalles.transacciones").exists());

        verify(classificationService, never()).classify(any());
    }

    @Test
    @DisplayName("Clasificar rechaza un valor negativo con 400")
    void clasificarRechazaValorNegativo() throws Exception {
        mockMvc.perform(post("/api/v1/clasificar-transacciones")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"transacciones\":[{\"descripcion\":\"Compra\",\"valor\":-5}]}"))
                .andExpect(status().isBadRequest());

        verify(classificationService, never()).classify(any());
    }
}
