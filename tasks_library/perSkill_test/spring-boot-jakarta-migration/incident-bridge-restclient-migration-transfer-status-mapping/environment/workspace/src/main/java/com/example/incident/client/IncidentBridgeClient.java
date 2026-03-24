package com.example.incident.client;

import com.example.incident.exception.IncidentBridgeServerException;
import com.example.incident.exception.IncidentFeedMissingException;
import com.example.incident.exception.IncidentRateLimitedException;
import java.io.IOException;
import java.net.URI;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.stereotype.Service;
import org.springframework.web.client.ResponseErrorHandler;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

@Service
public class IncidentBridgeClient {

    private final RestTemplate restTemplate;

    public IncidentBridgeClient(
        @Value("${incident.bridge.base-url:http://incident-bridge.example.internal}") String baseUrl
    ) {
        this.restTemplate = new RestTemplateBuilder()
            .rootUri(baseUrl)
            .errorHandler(new IncidentBridgeErrorHandler())
            .build();
    }

    public IncidentBatch pollEvents(String serviceName, String sinceToken, int batchSize) {
        ResponseEntity<IncidentBatch> response = restTemplate.exchange(
            buildEventsUri(serviceName, sinceToken, batchSize),
            HttpMethod.GET,
            new HttpEntity<>(defaultHeaders()),
            IncidentBatch.class
        );
        return response.getBody();
    }

    public FollowUpTicketResponse createFollowUpTicket(FollowUpTicketRequest request) {
        ResponseEntity<FollowUpTicketResponse> response = restTemplate.exchange(
            "/incident-feed/follow-up-tickets",
            HttpMethod.POST,
            new HttpEntity<>(request, defaultHeaders()),
            FollowUpTicketResponse.class
        );
        return response.getBody();
    }

    private String buildEventsUri(String serviceName, String sinceToken, int batchSize) {
        UriComponentsBuilder builder = UriComponentsBuilder.fromPath("/incident-feed/events")
            .queryParam("serviceName", serviceName)
            .queryParam("batchSize", batchSize);
        if (sinceToken != null && !sinceToken.isBlank()) {
            builder.queryParam("sinceToken", sinceToken);
        }
        return builder.build().toUriString();
    }

    private HttpHeaders defaultHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.setAccept(java.util.List.of(MediaType.APPLICATION_JSON));
        headers.setContentType(MediaType.APPLICATION_JSON);
        return headers;
    }

    private static final class IncidentBridgeErrorHandler implements ResponseErrorHandler {

        @Override
        public boolean hasError(ClientHttpResponse response) throws IOException {
            return response.getStatusCode().isError();
        }

        @Override
        public void handleError(URI url, HttpMethod method, ClientHttpResponse response) throws IOException {
            throw translate(response);
        }

        @Override
        public void handleError(ClientHttpResponse response) throws IOException {
            throw translate(response);
        }

        private RuntimeException translate(ClientHttpResponse response) throws IOException {
            int status = response.getStatusCode().value();
            if (status == 404) {
                return new IncidentFeedMissingException("Incident feed endpoint was not found");
            }
            if (status == 429) {
                return new IncidentRateLimitedException(
                    "Incident bridge is rate limiting requests",
                    parseRetryAfter(response.getHeaders().getFirst("Retry-After"))
                );
            }
            if (response.getStatusCode().is5xxServerError()) {
                return new IncidentBridgeServerException("Incident bridge failed upstream");
            }
            return new IllegalStateException("Unexpected response status: " + status);
        }

        private long parseRetryAfter(String retryAfterHeader) {
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
}
