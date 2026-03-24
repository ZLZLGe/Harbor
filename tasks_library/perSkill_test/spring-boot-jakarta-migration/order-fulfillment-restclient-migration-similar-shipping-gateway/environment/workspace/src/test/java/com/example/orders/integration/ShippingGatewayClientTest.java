package com.example.orders.integration;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.lang.reflect.Field;
import java.math.BigDecimal;
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
import static org.junit.jupiter.api.Assertions.assertTrue;

class ShippingGatewayClientTest {

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
    void usesConfiguredFluentHttpClient() {
        Field[] fields = ShippingGatewayClient.class.getDeclaredFields();
        boolean hasRestClient = false;
        boolean hasRestTemplate = false;
        for (Field field : fields) {
            hasRestClient = hasRestClient || field.getType().equals(RestClient.class);
            hasRestTemplate = hasRestTemplate || field.getType().getSimpleName().equals("RestTemplate");
        }
        assertTrue(hasRestClient, "ShippingGatewayClient should hold a RestClient instance");
        assertFalse(hasRestTemplate, "ShippingGatewayClient should no longer keep a RestTemplate field");
    }

    @Test
    void fetchQuotePreservesGetSemantics() throws Exception {
        AtomicReference<CapturedRequest> captured = new AtomicReference<>();
        server.createContext("/shipping/quotes", exchange -> {
            captured.set(capture(exchange));
            byte[] responseBody = """
                {"serviceLevel":"EXPRESS","feeAmount":12.50,"estimatedDays":2}
                """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, responseBody.length);
            exchange.getResponseBody().write(responseBody);
            exchange.close();
        });
        server.start();

        ShippingGatewayClient client = new ShippingGatewayClient(baseUrl());
        ShippingQuote quote = client.fetchQuote("94107", new BigDecimal("149.95"));

        assertNotNull(quote);
        assertEquals("EXPRESS", quote.serviceLevel());
        assertEquals(new BigDecimal("12.50"), quote.feeAmount());
        assertEquals(2, quote.estimatedDays());

        CapturedRequest request = captured.get();
        assertEquals("GET", request.method());
        assertEquals("application/json", request.accept());
        Map<String, String> query = parseQuery(request.pathAndQuery());
        assertEquals("94107", query.get("destinationZip"));
        assertEquals("149.95", query.get("declaredValue"));
    }

    @Test
    void createShipmentPreservesPostSemantics() throws Exception {
        AtomicReference<CapturedRequest> captured = new AtomicReference<>();
        server.createContext("/shipping/shipments", exchange -> {
            captured.set(capture(exchange));
            byte[] responseBody = """
                {"shipmentId":"ship-900","labelUrl":"https://labels.example/ship-900","status":"CREATED"}
                """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(201, responseBody.length);
            exchange.getResponseBody().write(responseBody);
            exchange.close();
        });
        server.start();

        ShippingGatewayClient client = new ShippingGatewayClient(baseUrl());
        ShipmentResponse response = client.createShipment(
            new ShipmentRequest("order-77", "10001", new BigDecimal("3.40"))
        );

        assertNotNull(response);
        assertEquals("ship-900", response.shipmentId());
        assertEquals("CREATED", response.status());

        CapturedRequest request = captured.get();
        assertEquals("POST", request.method());
        assertEquals("application/json", request.accept());
        assertEquals("application/json", request.contentType());
        assertEquals("/shipping/shipments", URI.create("http://localhost" + request.pathAndQuery()).getPath());
        assertEquals(
            "{\"orderId\":\"order-77\",\"destinationZip\":\"10001\",\"weightKg\":3.40}",
            request.body()
        );
    }

    @Test
    void cancelShipmentPreservesDeleteSemantics() throws Exception {
        AtomicReference<CapturedRequest> captured = new AtomicReference<>();
        server.createContext("/shipping/shipments", exchange -> {
            captured.set(capture(exchange));
            exchange.sendResponseHeaders(204, -1);
            exchange.close();
        });
        server.start();

        ShippingGatewayClient client = new ShippingGatewayClient(baseUrl());
        client.cancelShipment("ship-42", "duplicate-label");

        CapturedRequest request = captured.get();
        assertEquals("DELETE", request.method());
        assertEquals("application/json", request.accept());
        URI uri = URI.create("http://localhost" + request.pathAndQuery());
        assertEquals("/shipping/shipments/ship-42", uri.getPath());
        assertEquals("duplicate-label", parseQuery(request.pathAndQuery()).get("reason"));
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
        for (String part : uri.getQuery().split("&")) {
            String[] keyValue = part.split("=", 2);
            query.put(keyValue[0], keyValue.length > 1 ? keyValue[1] : "");
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
