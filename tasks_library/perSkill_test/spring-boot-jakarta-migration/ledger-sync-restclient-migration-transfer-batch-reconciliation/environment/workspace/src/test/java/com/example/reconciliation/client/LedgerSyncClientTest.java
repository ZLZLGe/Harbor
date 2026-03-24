package com.example.reconciliation.client;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.lang.reflect.Field;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
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
import static org.junit.jupiter.api.Assertions.assertTrue;

class LedgerSyncClientTest {

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
        Field[] fields = LedgerSyncClient.class.getDeclaredFields();
        boolean hasRestClient = false;
        boolean hasRestTemplate = false;

        for (Field field : fields) {
            hasRestClient = hasRestClient || field.getType().equals(RestClient.class);
            hasRestTemplate = hasRestTemplate || field.getType().getSimpleName().equals("RestTemplate");
        }

        assertTrue(hasRestClient, "LedgerSyncClient should keep a RestClient field");
        assertFalse(hasRestTemplate, "LedgerSyncClient should no longer keep a RestTemplate field");
    }

    @Test
    void fetchEntriesOmitsCursorOnFirstPageAndParsesGenericResponse() throws Exception {
        AtomicReference<CapturedRequest> captured = new AtomicReference<>();
        server.createContext("/ledger/entries", exchange -> {
            captured.set(capture(exchange));
            byte[] responseBody = """
                {"items":[{"entryId":"entry-100","amount":42.15,"currency":"USD","status":"OPEN"}],"nextCursor":"cursor-2","hasMore":true}
                """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, responseBody.length);
            exchange.getResponseBody().write(responseBody);
            exchange.close();
        });
        server.start();

        LedgerSyncClient client = new LedgerSyncClient(baseUrl());
        PageEnvelope<LedgerEntry> page = client.fetchEntries(null, 250, LocalDate.of(2025, 3, 1));

        assertNotNull(page);
        assertEquals(1, page.items().size());
        assertEquals("entry-100", page.items().get(0).entryId());
        assertEquals("cursor-2", page.nextCursor());
        assertTrue(page.hasMore());

        CapturedRequest request = captured.get();
        assertEquals("GET", request.method());
        assertEquals("application/json", request.accept());
        URI uri = URI.create("http://localhost" + request.pathAndQuery());
        assertEquals("/ledger/entries", uri.getPath());

        Map<String, String> query = parseQuery(request.pathAndQuery());
        assertEquals("250", query.get("limit"));
        assertEquals("2025-03-01", query.get("ledgerDate"));
        assertNull(query.get("cursor"));
    }

    @Test
    void fetchEntriesIncludesCursorOnSubsequentPages() throws Exception {
        AtomicReference<CapturedRequest> captured = new AtomicReference<>();
        server.createContext("/ledger/entries", exchange -> {
            captured.set(capture(exchange));
            byte[] responseBody = """
                {"items":[],"nextCursor":"cursor-3","hasMore":false}
                """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, responseBody.length);
            exchange.getResponseBody().write(responseBody);
            exchange.close();
        });
        server.start();

        LedgerSyncClient client = new LedgerSyncClient(baseUrl());
        PageEnvelope<LedgerEntry> page = client.fetchEntries("cursor-2", 100, LocalDate.of(2025, 3, 2));

        assertNotNull(page);
        CapturedRequest request = captured.get();
        Map<String, String> query = parseQuery(request.pathAndQuery());
        assertEquals("cursor-2", query.get("cursor"));
        assertEquals("100", query.get("limit"));
        assertEquals("2025-03-02", query.get("ledgerDate"));
    }

    @Test
    void submitConfirmationsPostsBatchJson() throws Exception {
        AtomicReference<CapturedRequest> captured = new AtomicReference<>();
        server.createContext("/ledger/entries/confirmations", exchange -> {
            captured.set(capture(exchange));
            byte[] responseBody = """
                {"batchId":"ack-55","acceptedCount":2}
                """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, responseBody.length);
            exchange.getResponseBody().write(responseBody);
            exchange.close();
        });
        server.start();

        LedgerSyncClient client = new LedgerSyncClient(baseUrl());
        LedgerAckResponse response = client.submitConfirmations(
            new LedgerConfirmationBatch(
                "run-2025-03-01",
                java.util.List.of(
                    new LedgerConfirmation("entry-100", "MATCHED"),
                    new LedgerConfirmation("entry-101", "SKIPPED")
                )
            )
        );

        assertNotNull(response);
        assertEquals("ack-55", response.batchId());
        assertEquals(2, response.acceptedCount());

        CapturedRequest request = captured.get();
        assertEquals("POST", request.method());
        assertEquals("application/json", request.accept());
        assertEquals("application/json", request.contentType());
        assertTrue(request.body().contains("\"reconciliationRunId\":\"run-2025-03-01\""));
        assertTrue(request.body().contains("\"entryId\":\"entry-100\""));
        assertTrue(request.body().contains("\"resolution\":\"SKIPPED\""));
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
