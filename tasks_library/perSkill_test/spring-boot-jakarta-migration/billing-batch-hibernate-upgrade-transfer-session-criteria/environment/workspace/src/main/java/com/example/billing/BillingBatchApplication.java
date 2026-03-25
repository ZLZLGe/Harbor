package com.example.billing;

import org.springframework.boot.WebApplicationType;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.builder.SpringApplicationBuilder;

@SpringBootApplication
public class BillingBatchApplication {

    public static void main(String[] args) {
        new SpringApplicationBuilder(BillingBatchApplication.class)
            .web(WebApplicationType.NONE)
            .run(args);
    }
}
