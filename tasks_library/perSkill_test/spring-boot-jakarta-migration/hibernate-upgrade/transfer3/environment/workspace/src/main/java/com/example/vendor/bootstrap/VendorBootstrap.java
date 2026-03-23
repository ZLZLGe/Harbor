package com.example.vendor.bootstrap;

import javax.annotation.PostConstruct;
import org.springframework.stereotype.Component;

@Component
public class VendorBootstrap {
    @PostConstruct
    public void init() {
        System.setProperty("vendor.bootstrap.ready", "true");
    }
}
