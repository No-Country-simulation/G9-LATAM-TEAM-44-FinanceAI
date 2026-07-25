package com.financeai.api.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/**
 * Cliente HTTP hacia el servicio de AI.
 *
 * Los timeouts son explicitos a proposito: sin ellos, si srv-python se cuelga,
 * el hilo de Tomcat se cuelga con el y la API entera deja de responder.
 */
@Configuration
@EnableConfigurationProperties(MlServiceProperties.class)
public class MlServiceConfig {

    @Bean
    public RestClient mlRestClient(MlServiceProperties properties) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout((int) properties.connectTimeout().toMillis());
        factory.setReadTimeout((int) properties.readTimeout().toMillis());

        return RestClient.builder()
                .baseUrl(properties.url())
                .requestFactory(factory)
                .defaultHeader("Accept", MediaType.APPLICATION_JSON_VALUE)
                .build();
    }
}
