#!/bin/bash

set -euo pipefail

cd /workspace

cat > src/main/java/com/example/orders/integration/ShippingGatewayClient.java <<'EOF'
package com.example.orders.integration;

import java.math.BigDecimal;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
public class ShippingGatewayClient {

    private final RestClient restClient;

    public ShippingGatewayClient(
        @Value("${shipping.gateway.base-url:https://shipping.example.internal}") String baseUrl
    ) {
        this.restClient = RestClient.builder()
            .baseUrl(baseUrl)
            .defaultHeader(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
            .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .build();
    }

    public ShippingQuote fetchQuote(String destinationZip, BigDecimal declaredValue) {
        return restClient.get()
            .uri(uriBuilder -> uriBuilder
                .path("/shipping/quotes")
                .queryParam("destinationZip", destinationZip)
                .queryParam("declaredValue", declaredValue)
                .build())
            .retrieve()
            .body(ShippingQuote.class);
    }

    public ShipmentResponse createShipment(ShipmentRequest shipmentRequest) {
        return restClient.post()
            .uri("/shipping/shipments")
            .body(shipmentRequest)
            .retrieve()
            .body(ShipmentResponse.class);
    }

    public void cancelShipment(String shipmentId, String reason) {
        restClient.delete()
            .uri(uriBuilder -> uriBuilder
                .path("/shipping/shipments/{shipmentId}")
                .queryParam("reason", reason)
                .build(shipmentId))
            .retrieve()
            .toBodilessEntity();
    }
}
EOF

mvn clean compile
mvn test
