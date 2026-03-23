package com.example.clinic.config;

import javax.annotation.PostConstruct;
import org.springframework.stereotype.Component;

@Component
public class IntakeBootstrap {
    @PostConstruct
    public void init() {
        System.setProperty("clinic.bootstrap.ready", "true");
    }
}
