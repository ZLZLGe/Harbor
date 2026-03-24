#!/bin/bash

set -euo pipefail

cd /workspace

cat > src/main/java/com/example/reporting/client/ArchiveExportClient.java <<'EOF'
package com.example.reporting.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
public class ArchiveExportClient {

    private static final MediaType TEXT_CSV = MediaType.parseMediaType("text/csv");

    private final RestClient restClient;

    public ArchiveExportClient(
        @Value("${report.archive.base-url:https://archive.example.internal}") String baseUrl
    ) {
        this.restClient = RestClient.builder()
            .baseUrl(baseUrl)
            .build();
    }

    public String downloadCsv(String exportId, String apiToken) {
        return restClient.get()
            .uri("/archive/exports/{exportId}/csv", exportId)
            .headers(headers -> headers.setBearerAuth(apiToken))
            .accept(TEXT_CSV)
            .retrieve()
            .body(String.class);
    }

    public byte[] downloadPdf(String exportId, String apiToken) {
        return restClient.get()
            .uri("/archive/exports/{exportId}/pdf", exportId)
            .headers(headers -> headers.setBearerAuth(apiToken))
            .accept(MediaType.APPLICATION_PDF)
            .retrieve()
            .body(byte[].class);
    }

    public ArchiveImportReceipt confirmImport(ArchiveImportConfirmation confirmation, String apiToken) {
        return restClient.post()
            .uri("/archive/import-confirmations")
            .headers(headers -> headers.setBearerAuth(apiToken))
            .contentType(MediaType.APPLICATION_JSON)
            .accept(MediaType.APPLICATION_JSON)
            .body(confirmation)
            .retrieve()
            .body(ArchiveImportReceipt.class);
    }
}
EOF

mvn clean compile
mvn test
