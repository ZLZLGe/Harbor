package com.example.billingbridge;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class InvoiceLedgerClientMigrationTest {

    private static final Path CLIENT_PATH = Path.of(
            "src/main/java/com/example/billingbridge/client/InvoiceLedgerClient.java"
    );

    @Test
    void clientUsesRestClientAndStatusHandler() throws IOException {
        String source = Files.readString(CLIENT_PATH);
        assertTrue(source.contains("RestClient"), "InvoiceLedgerClient should use RestClient");
        assertFalse(source.contains("RestTemplate"), "InvoiceLedgerClient should not use RestTemplate");
        assertTrue(source.contains("onStatus("), "InvoiceLedgerClient should define a status handler");
    }

    @Test
    void clientPreservesLedgerExceptionMapping() throws IOException {
        String source = Files.readString(CLIENT_PATH);
        assertTrue(source.contains("LedgerUnavailableException"), "Server errors should map to LedgerUnavailableException");
        assertTrue(source.contains(".toBodilessEntity()"), "Acknowledgement POST should finish with toBodilessEntity()");
    }
}
