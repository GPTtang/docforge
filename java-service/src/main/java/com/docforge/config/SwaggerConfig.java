package com.docforge.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class SwaggerConfig {

    @Bean
    public OpenAPI docForgeOpenAPI() {
        return new OpenAPI()
            .info(new Info()
                .title("DocForge API")
                .version("1.0.0")
                .description("DocForge API - Convert Word, Excel, PowerPoint, and PDF files into structured Markdown or JSON")
                .contact(new Contact()
                    .name("DocForge")
                    .url("https://github.com/GPTtang/docforge"))
                .license(new License()
                    .name("MIT License")
                    .url("https://opensource.org/licenses/MIT")));
    }
}