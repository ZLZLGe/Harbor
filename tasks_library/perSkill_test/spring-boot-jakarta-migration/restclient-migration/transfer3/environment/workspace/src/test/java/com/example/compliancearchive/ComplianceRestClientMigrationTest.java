package com.example.compliancearchive;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ComplianceRestClientMigrationTest {

    private static final Path CONFIG_PATH = Path.of(
            "src/main/java/com/example/compliancearchive/config/ComplianceRestClientConfig.java"
    );
    private static final Path CLIENT_PATH = Path.of(
            "src/main/java/com/example/compliancearchive/client/ComplianceArchiveClient.java"
    );

    @Test
    void configCreatesSharedRestClientBean() throws IOException {
        String configSource = Files.readString(CONFIG_PATH);
        assertTrue(configSource.contains("RestClient"), "Configuration should expose a RestClient bean");
        assertFalse(configSource.contains("RestTemplate"), "Configuration should not keep RestTemplate");
        assertTrue(configSource.contains(".baseUrl(baseUrl)"), "Configuration should set the base URL");
    }

    @Test
    void clientUsesInjectedBeanAndRelativeUris() throws IOException {
        String clientSource = Files.readString(CLIENT_PATH);
        assertTrue(clientSource.contains("RestClient"), "ComplianceArchiveClient should use RestClient");
        assertFalse(clientSource.contains("RestTemplate"), "ComplianceArchiveClient should not keep RestTemplate");
        assertTrue(clientSource.contains(".uri(\"/cases/{caseId}/archive\", caseId)"), "Archive POST should use a relative URI");
    }
}
