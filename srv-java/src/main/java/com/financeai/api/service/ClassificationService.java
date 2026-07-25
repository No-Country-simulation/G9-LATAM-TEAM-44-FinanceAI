package com.financeai.api.service;

import com.financeai.api.config.MlServiceProperties;
import com.financeai.api.dto.TransactionDTO;
import com.financeai.api.integration.FallbackClassifier;
import com.financeai.api.integration.PythonModelClient;
import com.financeai.api.integration.dto.ClasificarResponse;
import com.financeai.api.integration.dto.TransaccionClasificadaMl;
import com.financeai.api.integration.dto.TransaccionMl;
import com.financeai.api.model.FinancialCategory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Categoriza las transacciones y las agrega por categoria.
 *
 * Camino feliz: una sola llamada por lote a srv-python /clasificar.
 * Camino degradado: reglas por palabra clave locales ({@link FallbackClassifier}).
 */
@Service
public class ClassificationService {

    private static final Logger log = LoggerFactory.getLogger(ClassificationService.class);

    private final PythonModelClient modelClient;
    private final FallbackClassifier fallbackClassifier;
    private final MlServiceProperties properties;

    public ClassificationService(PythonModelClient modelClient,
                                 FallbackClassifier fallbackClassifier,
                                 MlServiceProperties properties) {
        this.modelClient = modelClient;
        this.fallbackClassifier = fallbackClassifier;
        this.properties = properties;
    }

    public ClassificationResult classify(List<TransactionDTO> transactions) {
        if (transactions == null || transactions.isEmpty()) {
            return new ClassificationResult(new LinkedHashMap<>(), false);
        }

        List<TransaccionMl> payload = transactions.stream()
                .map(t -> new TransaccionMl(t.descripcion(), t.valor()))
                .toList();

        Optional<ClasificarResponse> respuesta = modelClient.clasificar(payload);

        if (respuesta.isPresent() && esCoherente(respuesta.get(), transactions.size())) {
            return new ClassificationResult(agregarDesdeModelo(respuesta.get(), transactions), false);
        }

        if (respuesta.isPresent()) {
            log.warn("ml-service devolvio una respuesta incoherente con la peticion; se usa el respaldo local.");
        }
        return new ClassificationResult(agregarConRespaldo(transactions), true);
    }

    /**
     * El modelo debe devolver exactamente una categoria por transaccion enviada,
     * en el mismo orden. Si no, no podemos confiar en el emparejamiento.
     */
    private boolean esCoherente(ClasificarResponse respuesta, int esperadas) {
        List<TransaccionClasificadaMl> clasificadas = respuesta.transaccionesClasificadas();
        return clasificadas != null && clasificadas.size() == esperadas;
    }

    /**
     * Empareja por indice y usa SIEMPRE el valor de la transaccion original:
     * el monto es dato del backend, no del modelo. Del modelo solo tomamos la
     * categoria y la confianza.
     */
    private Map<String, Double> agregarDesdeModelo(ClasificarResponse respuesta,
                                                   List<TransactionDTO> originales) {
        Map<String, Double> resumen = new LinkedHashMap<>();
        List<TransaccionClasificadaMl> clasificadas = respuesta.transaccionesClasificadas();

        for (int i = 0; i < originales.size(); i++) {
            TransaccionClasificadaMl clasificada = clasificadas.get(i);
            FinancialCategory categoria = resolverCategoria(clasificada);
            resumen.merge(categoria.getValor(), originales.get(i).valor(), Double::sum);
        }
        return resumen;
    }

    /**
     * Aplica el umbral de confianza: por debajo de el preferimos "otras" antes
     * que arriesgar una categoria equivocada en un reporte financiero.
     */
    private FinancialCategory resolverCategoria(TransaccionClasificadaMl clasificada) {
        Double confianza = clasificada.confianza();
        if (confianza != null && confianza < properties.confianzaMinima()) {
            return FinancialCategory.OTRAS;
        }
        return FinancialCategory.desdeValor(clasificada.categoria());
    }

    private Map<String, Double> agregarConRespaldo(List<TransactionDTO> transactions) {
        Map<String, Double> resumen = new LinkedHashMap<>();
        for (TransactionDTO transaccion : transactions) {
            FinancialCategory categoria = fallbackClassifier.clasificar(transaccion.descripcion());
            resumen.merge(categoria.getValor(), transaccion.valor(), Double::sum);
        }
        return resumen;
    }
}
