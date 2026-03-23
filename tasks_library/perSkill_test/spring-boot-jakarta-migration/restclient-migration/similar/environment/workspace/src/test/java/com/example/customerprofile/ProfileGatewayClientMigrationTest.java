package com.example.customerprofile;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ProfileGatewayClientMigrationTest {

    private static final Path CLIENT_PATH = Path.of(
            "src/main/java/com/example/customerprofile/client/ProfileGatewayClient.java"
    );

    @Test
    void clientUsesRestClientInsteadOfRestTemplate() throws IOException {
        String source = Files.readString(CLIENT_PATH);
        assertTrue(source.contains("RestClient"), "ProfileGatewayClient should use RestClient");
        assertFalse(source.contains("RestTemplate"), "ProfileGatewayClient should not use RestTemplate");
    }

    @Test
    void clientUsesFluentRetrieveFlow() throws IOException {
        String source = Files.readString(CLIENT_PATH);
        assertTrue(source.contains(".retrieve()"), "ProfileGatewayClient should call retrieve()");
        assertTrue(source.contains(".toBodilessEntity()"), "Delete and POST flows should finish with toBodilessEntity()");
    }
}
