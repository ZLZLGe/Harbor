package com.example.compliancearchive.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

@Configuration
public class ComplianceRestClientConfig {

    @Bean
    public RestTemplate complianceRestTemplate() {
        return new RestTemplate();
    }
}
