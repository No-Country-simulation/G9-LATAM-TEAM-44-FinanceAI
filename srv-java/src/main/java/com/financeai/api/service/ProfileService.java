package com.financeai.api.service;

import com.financeai.api.dto.FactorDTO;
import com.financeai.api.dto.FinancialAnalysisRequestDTO;
import com.financeai.api.integration.PythonModelClient;
import com.financeai.api.integration.dto.FactorMl;
import com.financeai.api.integration.dto.PerfilRequest;
import com.financeai.api.integration.dto.PerfilResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * Determina el perfil financiero.
 *
 * Camino feliz: srv-python /perfil (modelo calibrado + factores explicativos).
 * Camino degradado: los mismos umbrales, calculados localmente.
 *
 * Los umbrales locales y los del stub de Python son identicos a proposito, asi
 * el reemplazo por el modelo real es un cambio de comportamiento controlado y
 * no una sorpresa el dia de la demo.
 */
@Service
public class ProfileService {

    private static final Logger log = LoggerFactory.getLogger(ProfileService.class);

    private static final String SALUDABLE = "Saludable";
    private static final String EN_OBSERVACION = "En observación";
    private static final String EN_RIESGO = "En riesgo";

    private static final Set<String> PERFILES_VALIDOS = Set.of(SALUDABLE, EN_OBSERVACION, EN_RIESGO);
    private static final Set<String> AHORRO_SUFICIENTE = Set.of("alta", "media");

    private final PythonModelClient modelClient;

    public ProfileService(PythonModelClient modelClient) {
        this.modelClient = modelClient;
    }

    public ProfileResult evaluar(FinancialAnalysisRequestDTO request, Map<String, Double> resumenGastos) {
        PerfilRequest peticion = new PerfilRequest(
                request.ingresoMensual(),
                request.nivelEndeudamiento(),
                request.frecuenciaAhorro(),
                resumenGastos
        );

        Optional<PerfilResponse> respuesta = modelClient.perfil(peticion);

        if (respuesta.isPresent() && esValida(respuesta.get())) {
            PerfilResponse perfil = respuesta.get();
            return new ProfileResult(
                    perfil.perfilFinanciero(),
                    perfil.probabilidad(),
                    aFactoresDTO(perfil.factores()),
                    false
            );
        }

        if (respuesta.isPresent()) {
            log.warn("ml-service devolvio un perfil fuera del contrato; se usan los umbrales locales.");
        }
        return calcularLocalmente(request, resumenGastos);
    }

    /** El perfil debe ser una de las tres etiquetas canonicas y traer probabilidad en [0,1]. */
    private boolean esValida(PerfilResponse perfil) {
        return perfil.perfilFinanciero() != null
                && PERFILES_VALIDOS.contains(perfil.perfilFinanciero())
                && perfil.probabilidad() != null
                && perfil.probabilidad() >= 0
                && perfil.probabilidad() <= 1;
    }

    private List<FactorDTO> aFactoresDTO(List<FactorMl> factores) {
        if (factores == null) {
            return List.of();
        }
        return factores.stream()
                .map(f -> new FactorDTO(f.nombre(), f.valor(), f.impacto()))
                .toList();
    }

    private ProfileResult calcularLocalmente(FinancialAnalysisRequestDTO request,
                                             Map<String, Double> resumenGastos) {
        double totalGastos = resumenGastos.values().stream()
                .mapToDouble(Double::doubleValue)
                .sum();
        double ingreso = request.ingresoMensual() == null ? 0.0 : request.ingresoMensual();
        double ratio = ingreso == 0 ? 1.0 : totalGastos / ingreso;
        int deuda = request.nivelEndeudamiento() == null ? 0 : request.nivelEndeudamiento();

        String perfil;
        double probabilidad;
        if (deuda >= 50 || ratio >= 1.0) {
            perfil = EN_RIESGO;
            probabilidad = 0.75;
        } else if (deuda >= 30 || ratio >= 0.8) {
            perfil = EN_OBSERVACION;
            probabilidad = 0.82;
        } else {
            perfil = SALUDABLE;
            probabilidad = 0.90;
        }

        boolean ahorraSuficiente = request.frecuenciaAhorro() != null
                && AHORRO_SUFICIENTE.contains(request.frecuenciaAhorro().trim().toLowerCase(Locale.ROOT));

        List<FactorDTO> factores = List.of(
                new FactorDTO("relacion_deuda_ingreso", redondear(deuda / 100.0),
                        deuda >= 30 ? "sube_riesgo" : "baja_riesgo"),
                new FactorDTO("tasa_gasto", redondear(ratio),
                        ratio >= 0.8 ? "sube_riesgo" : "baja_riesgo"),
                new FactorDTO("frecuencia_ahorro", ahorraSuficiente ? 1.0 : 0.0,
                        ahorraSuficiente ? "baja_riesgo" : "sube_riesgo")
        );

        return new ProfileResult(perfil, probabilidad, factores, true);
    }

    private double redondear(double valor) {
        return Math.round(valor * 1000.0) / 1000.0;
    }
}
