package com.financeai.api.service;

import com.financeai.api.dto.FinancialAnalysisRequestDTO;
import com.financeai.api.model.FinancialCategory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Motor de recomendaciones.
 *
 * Vive en Java y no en el modelo porque una recomendacion financiera es una
 * regla de negocio: hay que poder explicarla y cambiarla sin reentrenar.
 *
 * Los umbrales si salen de los datos. PATRON_SALUDABLE es la mediana del peso
 * de cada categoria entre los usuarios con perfil Saludable, calculada en el
 * notebook (seccion 12, "referencia_saludable" en artefactos/metadatos.json).
 * Con eso se pasa de "gasta menos" a "tu gasto en ocio pesa 2,3 veces lo que
 * pesa en un perfil saludable".
 *
 * Al reentrenar con datos nuevos hay que actualizar esta tabla.
 */
@Service
public class RecommendationService {

    /** Mediana del peso de cada categoria sobre el gasto total en perfiles saludables. */
    private static final Map<FinancialCategory, Double> PATRON_SALUDABLE = Map.of(
            FinancialCategory.ALIMENTACION, 0.052,
            FinancialCategory.TRANSPORTE, 0.063,
            FinancialCategory.SALUD, 0.080,
            FinancialCategory.VIVIENDA, 0.451,
            FinancialCategory.EDUCACION, 0.059,
            FinancialCategory.OCIO, 0.078,
            FinancialCategory.SERVICIOS, 0.096,
            FinancialCategory.OTRAS, 0.052
    );

    /** Proporcion tipica del ingreso que gasta un perfil saludable. */
    private static final double TASA_GASTO_SALUDABLE = 0.578;

    /** Categorias sobre las que se puede actuar a corto plazo. */
    private static final List<FinancialCategory> CATEGORIAS_ACCIONABLES = List.of(
            FinancialCategory.OCIO,
            FinancialCategory.OTRAS,
            FinancialCategory.TRANSPORTE,
            FinancialCategory.SERVICIOS
    );

    private static final double UMBRAL_DEUDA_ALTA = 40.0;
    private static final double DESVIACION_RELEVANTE = 1.5;
    private static final double PESO_MINIMO_PARA_MENCIONAR = 0.10;
    private static final int MAXIMO_RECOMENDACIONES = 4;

    public List<String> generateRecommendations(FinancialAnalysisRequestDTO request,
                                                Map<String, Double> resumenGastos) {

        double ingreso = request.ingresoMensual() == null ? 0.0 : request.ingresoMensual();
        int deuda = request.nivelEndeudamiento() == null ? 0 : request.nivelEndeudamiento();
        double totalGastos = resumenGastos.values().stream()
                .mapToDouble(Double::doubleValue)
                .sum();
        double tasaGasto = ingreso > 0 ? totalGastos / ingreso : 0.0;

        List<String> recomendaciones = new ArrayList<>();

        // De mayor a menor impacto: lo estructural primero, la categoria al final.
        agregarSobreGasto(recomendaciones, tasaGasto);
        agregarSobreDeuda(recomendaciones, deuda);
        agregarSobreAhorro(recomendaciones, request.frecuenciaAhorro());
        agregarCategoriasDesviadas(recomendaciones, resumenGastos, totalGastos);

        if (recomendaciones.isEmpty()) {
            recomendaciones.add("Tus indicadores están en rango saludable. Mantén el hábito y "
                    + "considera destinar el excedente a un fondo de emergencia equivalente a "
                    + "entre 3 y 6 meses de gastos.");
        }

        return recomendaciones.size() > MAXIMO_RECOMENDACIONES
                ? recomendaciones.subList(0, MAXIMO_RECOMENDACIONES)
                : recomendaciones;
    }

    private void agregarSobreGasto(List<String> recomendaciones, double tasaGasto) {
        if (tasaGasto >= 1.0) {
            recomendaciones.add("Tus gastos superan tu ingreso mensual: es la prioridad número uno. "
                    + "Identifica los dos gastos variables más grandes y recórtalos este mes.");
        } else if (tasaGasto >= TASA_GASTO_SALUDABLE * 1.25) {
            recomendaciones.add("Gastas el %.0f%% de tu ingreso, por encima del %.0f%% típico de un perfil saludable."
                    .formatted(tasaGasto * 100, TASA_GASTO_SALUDABLE * 100));
        }
    }

    private void agregarSobreDeuda(List<String> recomendaciones, int deuda) {
        if (deuda >= UMBRAL_DEUDA_ALTA) {
            recomendaciones.add("Tu nivel de endeudamiento (%d%%) supera el %.0f%% del ingreso. Prioriza "
                    .formatted(deuda, UMBRAL_DEUDA_ALTA)
                    + "amortizar la deuda de mayor interés antes de asumir nuevos compromisos.");
        }
    }

    private void agregarSobreAhorro(List<String> recomendaciones, String frecuenciaAhorro) {
        if (frecuenciaAhorro == null) {
            return;
        }
        String normalizada = frecuenciaAhorro.trim().toLowerCase(Locale.ROOT);
        if (normalizada.equals("baja") || normalizada.equals("nula")) {
            recomendaciones.add("Automatiza un ahorro fijo el mismo día que recibes tu ingreso, aunque "
                    + "sea pequeño: para construir el hábito importa más la constancia que el monto.");
        }
    }

    /**
     * Compara cada categoria accionable contra el patron saludable y menciona
     * como mucho las dos mas desviadas.
     *
     * El peso minimo evita el consejo inutil: una categoria puede estar al
     * triple del patron y ser el 2% del gasto, y ahi recortar no cambia nada.
     */
    private void agregarCategoriasDesviadas(List<String> recomendaciones,
                                            Map<String, Double> resumenGastos,
                                            double totalGastos) {
        if (totalGastos <= 0) {
            return;
        }

        record Desviacion(FinancialCategory categoria, double razon, double peso) {}
        List<Desviacion> desviaciones = new ArrayList<>();

        for (FinancialCategory categoria : CATEGORIAS_ACCIONABLES) {
            double gasto = resumenGastos.getOrDefault(categoria.getValor(), 0.0);
            double peso = gasto / totalGastos;
            double patron = PATRON_SALUDABLE.getOrDefault(categoria, 0.0);

            if (patron > 0 && peso > patron * DESVIACION_RELEVANTE && peso >= PESO_MINIMO_PARA_MENCIONAR) {
                desviaciones.add(new Desviacion(categoria, peso / patron, peso));
            }
        }

        desviaciones.stream()
                .sorted(Comparator.comparingDouble(Desviacion::razon).reversed())
                .limit(2)
                .forEach(d -> recomendaciones.add(
                        "Tu gasto en %s representa el %.0f%% del total, %.1f veces el patrón de un perfil saludable. Es la palanca más rápida para liberar margen."
                                .formatted(d.categoria().getValor(), d.peso() * 100, d.razon())));
    }
}
