#!/bin/bash

set -euo pipefail

cd /workspace

cat > src/main/java/com/example/reconciliation/client/LedgerSyncClient.java <<'EOF'
package com.example.reconciliation.client;

import java.time.LocalDate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
public class LedgerSyncClient {

    private final RestClient restClient;

    public LedgerSyncClient(
        @Value("${ledger.api.base-url:http://ledger.example.internal}") String baseUrl
    ) {
        this.restClient = RestClient.builder()
            .baseUrl(baseUrl)
            .defaultHeader(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
            .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .build();
    }

    public PageEnvelope<LedgerEntry> fetchEntries(String cursor, int limit, LocalDate ledgerDate) {
        return restClient.get()
            .uri(uriBuilder -> {
                var builder = uriBuilder.path("/ledger/entries")
                    .queryParam("limit", limit)
                    .queryParam("ledgerDate", ledgerDate);
                if (cursor != null && !cursor.isBlank()) {
                    builder = builder.queryParam("cursor", cursor);
                }
                return builder.build();
            })
            .retrieve()
            .body(new ParameterizedTypeReference<PageEnvelope<LedgerEntry>>() {
            });
    }

    public LedgerAckResponse submitConfirmations(LedgerConfirmationBatch batch) {
        return restClient.post()
            .uri("/ledger/entries/confirmations")
            .body(batch)
            .retrieve()
            .body(LedgerAckResponse.class);
    }
}
EOF

mvn clean compile
mvn test
