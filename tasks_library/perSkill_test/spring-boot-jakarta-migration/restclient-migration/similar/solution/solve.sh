#!/bin/bash
set -euo pipefail

cd /workspace

cat > src/main/java/com/example/customerprofile/client/ProfileGatewayClient.java <<'EOF'
package com.example.customerprofile.client;

import com.example.customerprofile.dto.CustomerProfile;
import com.example.customerprofile.dto.WelcomeMessageRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
public class ProfileGatewayClient {

    private final RestClient restClient;

    public ProfileGatewayClient(@Value("${profile.api.base-url}") String baseUrl) {
        this.restClient = RestClient.builder()
                .baseUrl(baseUrl)
                .build();
    }

    public CustomerProfile fetchProfile(String customerId) {
        return restClient.get()
                .uri("/profiles/{customerId}", customerId)
                .accept(MediaType.APPLICATION_JSON)
                .retrieve()
                .body(CustomerProfile.class);
    }

    public void sendWelcomeMessage(String customerId, String templateCode) {
        restClient.post()
                .uri("/notifications/welcome")
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.APPLICATION_JSON)
                .body(new WelcomeMessageRequest(customerId, templateCode))
                .retrieve()
                .toBodilessEntity();
    }

    public boolean deleteSnapshot(String customerId) {
        try {
            restClient.delete()
                    .uri("/snapshots/{customerId}", customerId)
                    .retrieve()
                    .toBodilessEntity();
            return true;
        } catch (RuntimeException ex) {
            return false;
        }
    }
}
EOF

mvn -q test
