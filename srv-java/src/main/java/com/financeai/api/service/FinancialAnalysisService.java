package com.financeai.api.service;

import com.financeai.api.dto.FinancialAnalysisRequestDTO;
import com.financeai.api.dto.FinancialAnalysisResponseDTO;
import com.financeai.api.integration.OCIStorageService;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

/**
 * Orquestador del analisis financiero.
 *
 * Flujo (particion "necesidad de saber"):
 *   1. /clasificar  -> solo transacciones      (srv-python nunca ve el ingreso)
 *   2. agregacion   -> resumen por categoria   (aqui, en Java)
 *   3. /perfil      -> solo agregados          (srv-python nunca ve descripciones)
 *   4. recomendaciones                          (reglas de negocio, siempre en Java)
 *
 * Solo este servicio ve el cuadro completo.
 */
@Service
public class FinancialAnalysisService {

    private final ClassificationService classificationService;
    private final ProfileService profileService;
    private final RecommendationService recommendationService;
    private final OCIStorageService ociStorageService;

    public FinancialAnalysisService(
            ClassificationService classificationService,
            ProfileService profileService,
            RecommendationService recommendationService,
            OCIStorageService ociStorageService) {
        this.classificationService = classificationService;
        this.profileService = profileService;
        this.recommendationService = recommendationService;
        this.ociStorageService = ociStorageService;
    }

    public FinancialAnalysisResponseDTO analyze(FinancialAnalysisRequestDTO request) {
        ClassificationResult clasificacion = classificationService.classify(request.transacciones());
        Map<String, Double> resumenGastos = clasificacion.resumenGastos();

        ProfileResult perfil = profileService.evaluar(request, resumenGastos);

        List<String> recomendaciones =
                recommendationService.generateRecommendations(request, resumenGastos);

        // Con que una de las dos etapas degrade, se marca: el consumidor tiene
        // que saber que el resultado no viene del modelo.
        boolean modoDegradado = clasificacion.modoDegradado() || perfil.modoDegradado();

        FinancialAnalysisResponseDTO respuesta = new FinancialAnalysisResponseDTO(
                perfil.perfilFinanciero(),
                perfil.probabilidad(),
                resumenGastos,
                recomendaciones,
                perfil.factores(),
                clasificacion.detalle(),
                modoDegradado
        );

        // Archivado en Object Storage, asincrono. Permite seguir la evolucion
        // en el tiempo sin meter latencia en el camino de la peticion.
        ociStorageService.guardarAnalisis(request, respuesta);

        return respuesta;
    }
}
