package com.example.reconciliation.batch;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.batch.core.BatchStatus;
import org.springframework.batch.core.JobExecution;
import org.springframework.batch.core.JobParametersBuilder;
import org.springframework.batch.test.JobLauncherTestUtils;
import org.springframework.batch.test.context.SpringBatchTest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@SpringBatchTest
@SpringBootTest
class LedgerReconciliationJobTest {

    private static final AtomicReference<CapturedRequest> FETCH_REQUEST = new AtomicReference<>();
    private static final AtomicReference<CapturedRequest> CONFIRM_REQUEST = new AtomicReference<>();
    private static final HttpServer SERVER = startServer();

    @Autowired
    private JobLauncherTestUtils jobLauncherTestUtils;

    @DynamicPropertySource
    static void registerProperties(DynamicPropertyRegistry registry) {
        registry.add("ledger.api.base-url", () -> "http://localhost:" + SERVER.getAddress().getPort());
    }

    @BeforeEach
    void resetCaptures() {
        FETCH_REQUEST.set(null);
        CONFIRM_REQUEST.set(null);
    }

    @AfterAll
    static void stopServer() {
        SERVER.stop(0);
    }

    @Test
    void launchesBatchJobAndSubmitsConfirmations() throws Exception {
        JobExecution execution = jobLauncherTestUtils.launchJob(
            new JobParametersBuilder()
                .addLong("launch.id", System.nanoTime())
                .toJobParameters()
        );

        assertEquals(BatchStatus.COMPLETED, execution.getStatus());
        assertNotNull(FETCH_REQUEST.get(), "job should fetch a ledger page");
        assertNotNull(CONFIRM_REQUEST.get(), "job should submit confirmations");
        assertTrue(FETCH_REQUEST.get().pathAndQuery().contains("limit=2"));
        assertTrue(FETCH_REQUEST.get().pathAndQuery().contains("ledgerDate=2025-03-01"));
        assertTrue(CONFIRM_REQUEST.get().body().contains("\"reconciliationRunId\":\"run-2025-03-01\""));
        assertTrue(CONFIRM_REQUEST.get().body().contains("\"entryId\":\"entry-200\""));
        assertEquals("POST", CONFIRM_REQUEST.get().method());
    }

    private static HttpServer startServer() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
            server.createContext("/ledger/entries", exchange -> {
                FETCH_REQUEST.set(capture(exchange));
                byte[] responseBody = """
                    {"items":[{"entryId":"entry-200","amount":88.70,"currency":"USD","status":"OPEN"}],"nextCursor":null,"hasMore":false}
                    """.getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().add("Content-Type", "application/json");
                exchange.sendResponseHeaders(200, responseBody.length);
                exchange.getResponseBody().write(responseBody);
                exchange.close();
            });
            server.createContext("/ledger/entries/confirmations", exchange -> {
                CONFIRM_REQUEST.set(capture(exchange));
                byte[] responseBody = """
                    {"batchId":"ack-200","acceptedCount":1}
                    """.getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().add("Content-Type", "application/json");
                exchange.sendResponseHeaders(200, responseBody.length);
                exchange.getResponseBody().write(responseBody);
                exchange.close();
            });
            server.start();
            return server;
        } catch (IOException exception) {
            throw new IllegalStateException("Failed to start test server", exception);
        }
    }

    private static CapturedRequest capture(HttpExchange exchange) throws IOException {
        String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        return new CapturedRequest(exchange.getRequestMethod(), exchange.getRequestURI().toString(), body);
    }

    private record CapturedRequest(
        String method,
        String pathAndQuery,
        String body
    ) {
    }
}
