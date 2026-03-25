package com.example.opsgateway.web;

import java.util.Map;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class GatewayController {

    @GetMapping(path = "/docs/index.html", produces = MediaType.TEXT_HTML_VALUE)
    public String docs() {
        return "<html><body><h1>Gateway Runbook</h1><p>Public ops documentation.</p></body></html>";
    }

    @GetMapping("/internal/ops/status")
    public Map<String, Object> internalStatus(Authentication authentication) {
        return Map.of(
                "surface", "internal",
                "principal", authentication.getName(),
                "status", "ops-ready");
    }

    @GetMapping("/api/v1/transfers")
    public Map<String, Object> transfers(Authentication authentication) {
        return Map.of(
                "surface", "api",
                "principal", authentication.getName(),
                "mode", "stateless");
    }
}
