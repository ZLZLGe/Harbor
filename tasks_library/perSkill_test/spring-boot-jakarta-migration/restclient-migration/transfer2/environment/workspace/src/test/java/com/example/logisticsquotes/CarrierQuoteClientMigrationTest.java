package com.example.logisticsquotes;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class CarrierQuoteClientMigrationTest {

    private static final Path CLIENT_PATH = Path.of(
            "src/main/java/com/example/logisticsquotes/client/CarrierQuoteClient.java"
    );

    @Test
    void clientUsesRestClientForGenericResponses() throws IOException {
        String source = Files.readString(CLIENT_PATH);
        assertTrue(source.contains("RestClient"), "CarrierQuoteClient should use RestClient");
        assertFalse(source.contains("RestTemplate"), "CarrierQuoteClient should not use RestTemplate");
        assertTrue(
                source.contains("new ParameterizedTypeReference<List<CarrierQuote>>()"),
                "CarrierQuoteClient should keep a typed generic response"
        );
    }

    @Test
    void clientUsesUriBuilderAndDeleteFlow() throws IOException {
        String source = Files.readString(CLIENT_PATH);
        assertTrue(source.contains("uri(uriBuilder ->"), "Quote lookup should use a URI builder");
        assertTrue(source.contains(".delete()"), "Quote cancellation should use RestClient delete()");
    }
}
