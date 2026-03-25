package com.acme.claims.service;

import java.util.HashMap;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

@Service
public class RiskGateway {

    private final RestTemplate restTemplate;
    private final String baseUrl;

    public RiskGateway(RestTemplate restTemplate, @Value("${risk.base-url}") String baseUrl) {
        this.restTemplate = restTemplate;
        this.baseUrl = baseUrl;
    }

    public RiskDecision evaluate(String policyNumber, String claimantEmail) {
        Map<String, String> payload = new HashMap<>();
        payload.put("policyNumber", policyNumber);
        payload.put("claimantEmail", claimantEmail);

        ResponseEntity<RiskDecision> response = restTemplate.postForEntity(
                baseUrl + "/screenings",
                payload,
                RiskDecision.class);

        return response.getBody() == null ? new RiskDecision(0, false) : response.getBody();
    }
}
