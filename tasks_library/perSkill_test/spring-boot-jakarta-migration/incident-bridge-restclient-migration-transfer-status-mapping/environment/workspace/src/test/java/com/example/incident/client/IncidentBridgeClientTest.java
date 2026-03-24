package com.example.incident.client;

import com.example.incident.exception.IncidentBridgeServerException;
import com.example.incident.exception.IncidentFeedMissingException;
import com.example.incident.exception.IncidentRateLimitedException;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.lang.reflect.Field;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class IncidentBridgeClientTest {

    private HttpServer server;

    @BeforeEach
    void setUp() throws IOException {
        server = HttpServer.create(new InetSocketAddress(0), 0);
    }

    @AfterEach
    void tearDown() {
        server.stop(0);
    }

    @Test
    void usesRestClientInsteadOfRestTemplate() {
        Field[] fields = IncidentBridgeClient.class.getDeclaredFields();
        boolean hasRestClient = false;
        boolean hasRestTemplate = false;

        for (Field field : fields) {
            hasRestClient = hasRestClient || field.getType().equals(RestClient.class);
            hasRestTemplate = hasRestTemplate || field.getType().getSimpleName().equals("RestTemplate");
        }

        assertTrue(hasRestClient, "IncidentBridgeClient should keep a RestClient field");
        assertFalse(hasRestTemplate, "IncidentBridgeClient should no longer keep a RestTemplate field");
    }

    @Test
    void pollEventsPreservesRequestShapeAndParsesResponse() throws Exception {
        AtomicReference<CapturedRequest> captured = new AtomicReference<>();
        server.createContext("/incident-feed/events", exchange -> {
            captured.set(capture(exchange));
            byte[] responseBody = """
                {"events":[{"incidentId":"inc-401","serviceName":"payments-api","severity":"SEV1","summary":"Card processing stalled"}],"resumeToken":"evt-402"}
                """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, responseBody.length);
            exchange.getResponseBody().write(responseBody);
            exchange.close();
        });
        server.start();

        IncidentBridgeClient client = new IncidentBridgeClient(baseUrl());
        IncidentBatch batch = client.pollEvents("payments-api", null, 25);

        assertNotNull(batch);
        assertEquals(1, batch.events().size());
        assertEquals("inc-401", batch.events().get(0).incidentId());
        assertEquals("evt-402", batch.resumeToken());

        CapturedRequest request = captured.get();
        assertEquals("GET", request.method());
        assertTrue(request.accept().contains("application/json"));

        Map<String, String> query = parseQuery(request.pathAndQuery());
        assertEquals("payments-api", query.get("serviceName"));
        assertEquals("25", query.get("batchSize"));
        assertNull(query.get("sinceToken"));
    }

    @Test
    void pollEventsIncludesSinceTokenWhenPresent() throws Exception {
        AtomicReference<CapturedRequest> captured = new AtomicReference<>();
        server.createContext("/incident-feed/events", exchange -> {
            captured.set(capture(exchange));
            byte[] responseBody = """
                {"events":[],"resumeToken":"evt-900"}
                """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, responseBody.length);
            exchange.getResponseBody().write(responseBody);
            exchange.close();
        });
        server.start();

        IncidentBridgeClient client = new IncidentBridgeClient(baseUrl());
        client.pollEvents("identity-api", "evt-899", 10);

        Map<String, String> query = parseQuery(captured.get().pathAndQuery());
        assertEquals("identity-api", query.get("serviceName"));
        assertEquals("10", query.get("batchSize"));
        assertEquals("evt-899", query.get("sinceToken"));
    }

    @Test
    void createFollowUpTicketPostsJsonPayload() throws Exception {
        AtomicReference<CapturedRequest> captured = new AtomicReference<>();
        server.createContext("/incident-feed/follow-up-tickets", exchange -> {
            captured.set(capture(exchange));
            byte[] responseBody = """
                {"ticketId":"ticket-81","status":"CREATED"}
                """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, responseBody.length);
            exchange.getResponseBody().write(responseBody);
            exchange.close();
        });
        server.start();

        IncidentBridgeClient client = new IncidentBridgeClient(baseUrl());
        FollowUpTicketResponse response = client.createFollowUpTicket(
            new FollowUpTicketRequest("inc-401", "sre-primary", "Escalate SEV1 card outage")
        );

        assertNotNull(response);
        assertEquals("ticket-81", response.ticketId());
        assertEquals("CREATED", response.status());

        CapturedRequest request = captured.get();
        assertEquals("POST", request.method());
        assertTrue(request.accept().contains("application/json"));
        assertTrue(request.contentType().contains("application/json"));
        assertTrue(request.body().contains("\"incidentId\":\"inc-401\""));
        assertTrue(request.body().contains("\"assignmentGroup\":\"sre-primary\""));
        assertTrue(request.body().contains("\"note\":\"Escalate SEV1 card outage\""));
    }

    @Test
    void maps404ToIncidentFeedMissingException() throws Exception {
        server.createContext("/incident-feed/events", exchange -> {
            exchange.sendResponseHeaders(404, -1);
            exchange.close();
        });
        server.start();

        IncidentBridgeClient client = new IncidentBridgeClient(baseUrl());

        IncidentFeedMissingException error = assertThrows(
            IncidentFeedMissingException.class,
            () -> client.pollEvents("payments-api", null, 25)
        );

        assertTrue(error.getMessage().contains("not found"));
    }

    @Test
    void maps429ToIncidentRateLimitedExceptionAndKeepsRetryAfter() throws Exception {
        server.createContext("/incident-feed/events", exchange -> {
            exchange.getResponseHeaders().add("Retry-After", "17");
            exchange.sendResponseHeaders(429, -1);
            exchange.close();
        });
        server.start();

        IncidentBridgeClient client = new IncidentBridgeClient(baseUrl());

        IncidentRateLimitedException error = assertThrows(
            IncidentRateLimitedException.class,
            () -> client.pollEvents("payments-api", "evt-402", 25)
        );

        assertEquals(17L, error.getRetryAfterSeconds());
    }

    @Test
    void maps5xxToIncidentBridgeServerException() throws Exception {
        server.createContext("/incident-feed/events", exchange -> {
            exchange.sendResponseHeaders(503, -1);
            exchange.close();
        });
        server.start();

        IncidentBridgeClient client = new IncidentBridgeClient(baseUrl());

        assertThrows(
            IncidentBridgeServerException.class,
            () -> client.pollEvents("payments-api", null, 25)
        );
    }

    private String baseUrl() {
        return "http://localhost:" + server.getAddress().getPort();
    }

    private CapturedRequest capture(HttpExchange exchange) throws IOException {
        String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        return new CapturedRequest(
            exchange.getRequestMethod(),
            exchange.getRequestURI().toString(),
            exchange.getRequestHeaders().getFirst("Accept"),
            exchange.getRequestHeaders().getFirst("Content-Type"),
            body
        );
    }

    private Map<String, String> parseQuery(String pathAndQuery) {
        URI uri = URI.create("http://localhost" + pathAndQuery);
        Map<String, String> query = new HashMap<>();
        if (uri.getQuery() == null || uri.getQuery().isBlank()) {
            return query;
        }
        for (String entry : uri.getQuery().split("&")) {
            String[] parts = entry.split("=", 2);
            query.put(parts[0], parts.length > 1 ? parts[1] : "");
        }
        return query;
    }

    private record CapturedRequest(
        String method,
        String pathAndQuery,
        String accept,
        String contentType,
        String body
    ) {
    }
}
