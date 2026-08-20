package com.financeai.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Configuracion de OCI Object Storage.
 *
 * El acceso va por Pre-Authenticated Request (PAR): una URL firmada con
 * caducidad que permite escribir sin credenciales en el contenedor ni el SDK
 * completo de OCI, que son decenas de MB para subir un JSON.
 *
 * Para listar objetos o gestionar permisos por usuario habria que pasar al SDK
 * con instance principals. El cambio queda acotado a
 * {@link com.financeai.api.integration.OCIStorageService}.
 *
 * @param parUrl              URL de la PAR con permiso de escritura, terminada en /
 * @param bucket              nombre del bucket (solo informativo en el diagnostico)
 * @param namespace           namespace de Object Storage (idem)
 * @param region              region de OCI (idem)
 * @param prefijo             carpeta logica dentro del bucket
 * @param historialHabilitado si false, no se persiste ningun analisis
 */
@ConfigurationProperties(prefix = "oci")
public record OciProperties(
        String parUrl,
        String bucket,
        String namespace,
        String region,
        String prefijo,
        Boolean historialHabilitado
) {

    public OciProperties {
        if (bucket == null || bucket.isBlank()) {
            bucket = "finance-ai-models";
        }
        if (prefijo == null) {
            prefijo = "historial";
        }
        if (historialHabilitado == null) {
            historialHabilitado = Boolean.TRUE;
        }
        if (parUrl != null && !parUrl.isBlank() && !parUrl.endsWith("/")) {
            parUrl = parUrl + "/";
        }
    }

    /** True si hay una PAR configurada y el historial no esta apagado. */
    public boolean puedeEscribir() {
        return historialHabilitado && parUrl != null && !parUrl.isBlank();
    }
}
