package com.example.reporting.client;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.lang.reflect.Field;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ArchiveExportClientTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

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
        Field[] fields = ArchiveExportClient.class.getDeclaredFields();
        boolean hasRestClient = false;
        boolean hasRestTemplate = false;
        for (Field field : fields) {
            hasRestClient = hasRestClient || field.getType().equals(RestClient.class);
            hasRestTemplate = hasRestTemplate || field.getType().getSimpleName().equals("RestTemplate");
        }
        assertTrue(hasRestClient, "ArchiveExportClient should hold a RestClient instance");
        assertFalse(hasRestTemplate, "ArchiveExportClient should no longer keep a RestTemplate field");
    }

    @Test
    void downloadCsvPreservesBearerAuthAndTextBody() throws Exception {
        AtomicReference<CapturedRequest> captured = new AtomicReference<>();
        server.createContext("/archive/exports/", exchange -> {
            captured.set(capture(exchange));
            byte[] responseBody = "row_id,total\nA-10,12\n".getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "text/csv");
            exchange.sendResponseHeaders(200, responseBody.length);
            exchange.getResponseBody().write(responseBody);
            exchange.close();
        });
        server.start();

        ArchiveExportClient client = new ArchiveExportClient(baseUrl());
        String csv = client.downloadCsv("exp-44", "archive-token");

        assertEquals("row_id,total\nA-10,12\n", csv);

        CapturedRequest request = captured.get();
        assertNotNull(request);
        assertEquals("GET", request.method());
        assertEquals("/archive/exports/exp-44/csv", URI.create("http://localhost" + request.pathAndQuery()).getPath());
        assertEquals("Bearer archive-token", request.authorization());
        assertEquals("text/csv", request.accept());
    }

    @Test
    void downloadPdfPreservesBearerAuthAndBinaryBody() throws Exception {
        AtomicReference<CapturedRequest> captured = new AtomicReference<>();
        byte[] pdfBytes = new byte[] {37, 80, 68, 70, 45, 49, 46, 55, 10, 0, 10};
        server.createContext("/archive/exports/", exchange -> {
            captured.set(capture(exchange));
            exchange.getResponseHeaders().add("Content-Type", "application/pdf");
            exchange.sendResponseHeaders(200, pdfBytes.length);
            exchange.getResponseBody().write(pdfBytes);
            exchange.close();
        });
        server.start();

        ArchiveExportClient client = new ArchiveExportClient(baseUrl());
        byte[] body = client.downloadPdf("exp-55", "binary-token");

        assertArrayEquals(pdfBytes, body);

        CapturedRequest request = captured.get();
        assertNotNull(request);
        assertEquals("GET", request.method());
        assertEquals("/archive/exports/exp-55/pdf", URI.create("http://localhost" + request.pathAndQuery()).getPath());
        assertEquals("Bearer binary-token", request.authorization());
        assertEquals("application/pdf", request.accept());
    }

    @Test
    void confirmImportPreservesJsonContract() throws Exception {
        AtomicReference<CapturedRequest> captured = new AtomicReference<>();
        server.createContext("/archive/import-confirmations", exchange -> {
            captured.set(capture(exchange));
            byte[] responseBody = """
                {"confirmationId":"ack-900","status":"RECORDED","acceptedAt":"2026-02-19T12:30:00Z"}
                """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, responseBody.length);
            exchange.getResponseBody().write(responseBody);
            exchange.close();
        });
        server.start();

        ArchiveExportClient client = new ArchiveExportClient(baseUrl());
        ArchiveImportReceipt receipt = client.confirmImport(
            new ArchiveImportConfirmation(
                "exp-90",
                "/archives/2026/exp-90.csv",
                "sha256:abc123",
                "2026-02-19T12:28:00Z",
                true
            ),
            "confirm-token"
        );

        assertNotNull(receipt);
        assertEquals("ack-900", receipt.confirmationId());
        assertEquals("RECORDED", receipt.status());
        assertEquals("2026-02-19T12:30:00Z", receipt.acceptedAt());

        CapturedRequest request = captured.get();
        assertNotNull(request);
        assertEquals("POST", request.method());
        assertEquals("/archive/import-confirmations", URI.create("http://localhost" + request.pathAndQuery()).getPath());
        assertEquals("Bearer confirm-token", request.authorization());
        assertTrue(request.contentType().startsWith("application/json"));

        Map<String, Object> payload = objectMapper.readValue(request.body(), new TypeReference<>() {});
        assertEquals("exp-90", payload.get("exportId"));
        assertEquals("/archives/2026/exp-90.csv", payload.get("archivePath"));
        assertEquals("sha256:abc123", payload.get("checksum"));
        assertEquals("2026-02-19T12:28:00Z", payload.get("importedAt"));
        assertEquals(Boolean.TRUE, payload.get("successful"));
    }

    private String baseUrl() {
        return "http://localhost:" + server.getAddress().getPort();
    }

    private CapturedRequest capture(HttpExchange exchange) throws IOException {
        String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        return new CapturedRequest(
            exchange.getRequestMethod(),
            exchange.getRequestURI().toString(),
            exchange.getRequestHeaders().getFirst("Authorization"),
            exchange.getRequestHeaders().getFirst("Accept"),
            exchange.getRequestHeaders().getFirst("Content-Type"),
            body
        );
    }

    private record CapturedRequest(
        String method,
        String pathAndQuery,
        String authorization,
        String accept,
        String contentType,
        String body
    ) {
    }
}
