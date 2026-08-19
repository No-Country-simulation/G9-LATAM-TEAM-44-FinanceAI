package com.financeai.api.service;

import com.financeai.api.dto.FactorDTO;
import com.financeai.api.dto.FinancialAnalysisRequestDTO;
import com.financeai.api.integration.PythonModelClient;
import com.financeai.api.integration.dto.FactorMl;
import com.financeai.api.integration.dto.PerfilRequest;
import com.financeai.api.integration.dto.PerfilResponse;
import com.financeai.api.model.FinancialProfile;
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
 * Los umbrales del respaldo son identicos a los de _perfil_con_reglas en
 * srv-python, para que el diagnostico no cambie segun quien lo calcule.
 */
@Service
public class ProfileService {

    private static final Logger log = LoggerFactory.getLogger(ProfileService.class);

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
            // Se reemite la forma canonica: si el modelo responde
            // "En observacion" sin tilde, la API sigue devolviendo la version
            // con tilde y el cliente no ve dos escrituras de lo mismo.
            return new ProfileResult(
                    FinancialProfile.desdeValor(perfil.perfilFinanciero()).getValor(),
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
        return FinancialProfile.esValido(perfil.perfilFinanciero())
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

        FinancialProfile perfil;
        double probabilidad;
        if (deuda >= 50 || ratio >= 1.0) {
            perfil = FinancialProfile.EN_RIESGO;
            probabilidad = 0.75;
        } else if (deuda >= 30 || ratio >= 0.8) {
            perfil = FinancialProfile.EN_OBSERVACION;
            probabilidad = 0.82;
        } else {
            perfil = FinancialProfile.SALUDABLE;
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

        return new ProfileResult(perfil.getValor(), probabilidad, factores, true);
    }

    private double redondear(double valor) {
        return Math.round(valor * 1000.0) / 1000.0;
    }
}
