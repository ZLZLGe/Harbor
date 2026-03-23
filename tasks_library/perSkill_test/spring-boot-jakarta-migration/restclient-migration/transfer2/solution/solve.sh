#!/bin/bash
set -euo pipefail

cd /workspace

cat > src/main/java/com/example/logisticsquotes/client/CarrierQuoteClient.java <<'EOF'
package com.example.logisticsquotes.client;

import com.example.logisticsquotes.dto.CarrierQuote;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.List;

@Service
public class CarrierQuoteClient {

    private final RestClient restClient;

    public CarrierQuoteClient(@Value("${quotes.api.base-url}") String baseUrl) {
        this.restClient = RestClient.builder()
                .baseUrl(baseUrl)
                .build();
    }

    public List<CarrierQuote> lookupQuotes(String origin, String destination, int weightKg) {
        List<CarrierQuote> body = restClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path("/quotes/search")
                        .queryParam("origin", origin)
                        .queryParam("destination", destination)
                        .queryParam("weightKg", weightKg)
                        .build())
                .accept(MediaType.APPLICATION_JSON)
                .retrieve()
                .body(new ParameterizedTypeReference<List<CarrierQuote>>() {
                });
        return body == null ? List.of() : body;
    }

    public void cancelQuote(String quoteRequestId) {
        restClient.delete()
                .uri("/quotes/requests/{quoteRequestId}", quoteRequestId)
                .retrieve()
                .toBodilessEntity();
    }
}
EOF

mvn -q test
