package com.financeai.api.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI financeAiOpenAPI() {
        return new OpenAPI().info(new Info()
                .title("Finance AI API")
                .version("1.0.0-MVP")
                .description("API REST para análisis básico de salud financiera."));
    }
}
