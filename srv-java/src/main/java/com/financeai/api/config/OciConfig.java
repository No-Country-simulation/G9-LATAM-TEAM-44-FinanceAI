package com.financeai.api.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/** Activa el enlace de las propiedades {@code oci.*}. */
@Configuration
@EnableConfigurationProperties(OciProperties.class)
public class OciConfig {
}
