package com.financeai.api.service;

import com.financeai.api.config.MlServiceProperties;
import com.financeai.api.dto.ClassifiedTransactionDTO;
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

import java.util.ArrayList;
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
            return new ClassificationResult(List.of(), new LinkedHashMap<>(), false);
        }

        List<TransaccionMl> payload = transactions.stream()
                .map(t -> new TransaccionMl(t.descripcion(), t.valor()))
                .toList();

        Optional<ClasificarResponse> respuesta = modelClient.clasificar(payload);

        if (respuesta.isPresent() && esCoherente(respuesta.get(), transactions.size())) {
            return construirDesdeModelo(respuesta.get(), transactions);
        }

        if (respuesta.isPresent()) {
            log.warn("ml-service devolvio una respuesta incoherente con la peticion; se usa el respaldo local.");
        }
        return construirConRespaldo(transactions);
    }

    /**
     * Una categoria por transaccion enviada y en el mismo orden. Si no coincide,
     * el emparejamiento por indice no es fiable.
     */
    private boolean esCoherente(ClasificarResponse respuesta, int esperadas) {
        List<TransaccionClasificadaMl> clasificadas = respuesta.transaccionesClasificadas();
        return clasificadas != null && clasificadas.size() == esperadas;
    }

    /**
     * Empareja por indice. El monto sale de la transaccion original; del modelo
     * solo se toman categoria y confianza.
     */
    private ClassificationResult construirDesdeModelo(ClasificarResponse respuesta,
                                                      List<TransactionDTO> originales) {
        Map<String, Double> resumen = resumenVacio();
        List<ClassifiedTransactionDTO> detalle = new ArrayList<>(originales.size());
        List<TransaccionClasificadaMl> clasificadas = respuesta.transaccionesClasificadas();

        for (int i = 0; i < originales.size(); i++) {
            TransactionDTO original = originales.get(i);
            TransaccionClasificadaMl clasificada = clasificadas.get(i);

            FinancialCategory categoria = resolverCategoria(clasificada);
            double confianza = clasificada.confianza() == null ? 0.0 : clasificada.confianza();

            resumen.merge(categoria.getValor(), original.valor(), Double::sum);
            detalle.add(new ClassifiedTransactionDTO(
                    original.descripcion(), original.valor(), categoria.getValor(), confianza));
        }
        return new ClassificationResult(detalle, resumen, false);
    }

    /**
     * Umbral de confianza: por debajo, "otras". En un reporte financiero un
     * gasto sin clasificar molesta menos que uno mal atribuido.
     */
    private FinancialCategory resolverCategoria(TransaccionClasificadaMl clasificada) {
        Double confianza = clasificada.confianza();
        if (confianza != null && confianza < properties.confianzaMinima()) {
            return FinancialCategory.OTRAS;
        }
        return FinancialCategory.desdeValor(clasificada.categoria());
    }

    private ClassificationResult construirConRespaldo(List<TransactionDTO> transactions) {
        Map<String, Double> resumen = resumenVacio();
        List<ClassifiedTransactionDTO> detalle = new ArrayList<>(transactions.size());

        for (TransactionDTO transaccion : transactions) {
            FinancialCategory categoria = fallbackClassifier.clasificar(transaccion.descripcion());
            double confianza = categoria == FinancialCategory.OTRAS
                    ? FallbackClassifier.CONFIANZA_SIN_MATCH
                    : FallbackClassifier.CONFIANZA_KEYWORD;

            resumen.merge(categoria.getValor(), transaccion.valor(), Double::sum);
            detalle.add(new ClassifiedTransactionDTO(
                    transaccion.descripcion(), transaccion.valor(), categoria.getValor(), confianza));
        }
        return new ClassificationResult(detalle, resumen, true);
    }

    /**
     * Resumen vacio.
     *
     * Solo se incluyen las categorias con gasto, como en el ejemplo del reto.
     * El frontend trata la ausencia de una clave como cero.
     *
     * LinkedHashMap para que el orden en el JSON sea el de aparicion y no
     * cambie entre peticiones identicas.
     */
    private Map<String, Double> resumenVacio() {
        return new LinkedHashMap<>();
    }
}
