#!/bin/bash

set -euo pipefail

cd /workspace

cat > src/main/java/com/example/incident/client/IncidentBridgeClient.java <<'EOF'
package com.example.incident.client;

import com.example.incident.exception.IncidentBridgeServerException;
import com.example.incident.exception.IncidentFeedMissingException;
import com.example.incident.exception.IncidentRateLimitedException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
public class IncidentBridgeClient {

    private final RestClient restClient;

    public IncidentBridgeClient(
        @Value("${incident.bridge.base-url:http://incident-bridge.example.internal}") String baseUrl
    ) {
        this.restClient = RestClient.builder()
            .baseUrl(baseUrl)
            .defaultHeader(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
            .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .defaultStatusHandler(
                statusCode -> statusCode.value() == 404,
                (request, response) -> {
                    throw new IncidentFeedMissingException("Incident feed endpoint was not found");
                }
            )
            .defaultStatusHandler(
                statusCode -> statusCode.value() == 429,
                (request, response) -> {
                    throw new IncidentRateLimitedException(
                        "Incident bridge is rate limiting requests",
                        parseRetryAfter(response.getHeaders().getFirst("Retry-After"))
                    );
                }
            )
            .defaultStatusHandler(
                HttpStatusCode::is5xxServerError,
                (request, response) -> {
                    throw new IncidentBridgeServerException("Incident bridge failed upstream");
                }
            )
            .build();
    }

    public IncidentBatch pollEvents(String serviceName, String sinceToken, int batchSize) {
        return restClient.get()
            .uri(uriBuilder -> {
                var builder = uriBuilder
                    .path("/incident-feed/events")
                    .queryParam("serviceName", serviceName)
                    .queryParam("batchSize", batchSize);
                if (sinceToken != null && !sinceToken.isBlank()) {
                    builder = builder.queryParam("sinceToken", sinceToken);
                }
                return builder.build();
            })
            .retrieve()
            .body(IncidentBatch.class);
    }

    public FollowUpTicketResponse createFollowUpTicket(FollowUpTicketRequest request) {
        return restClient.post()
            .uri("/incident-feed/follow-up-tickets")
            .body(request)
            .retrieve()
            .body(FollowUpTicketResponse.class);
    }

    private static long parseRetryAfter(String retryAfterHeader) {
        if (retryAfterHeader == null || retryAfterHeader.isBlank()) {
            return 0L;
        }
        try {
            return Long.parseLong(retryAfterHeader);
        } catch (NumberFormatException ex) {
            return 0L;
        }
    }
}
EOF

mvn clean compile
mvn test
