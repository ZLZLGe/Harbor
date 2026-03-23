#!/bin/bash
set -euo pipefail

cd /workspace

cat > src/main/java/com/example/billingbridge/client/InvoiceLedgerClient.java <<'EOF'
package com.example.billingbridge.client;

import com.example.billingbridge.dto.InvoiceStatusRecord;
import com.example.billingbridge.exception.LedgerUnavailableException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.Map;

@Service
public class InvoiceLedgerClient {

    private final RestClient restClient;

    public InvoiceLedgerClient(@Value("${ledger.api.base-url}") String baseUrl) {
        this.restClient = RestClient.builder()
                .baseUrl(baseUrl)
                .build();
    }

    public InvoiceStatusRecord fetchInvoice(String invoiceId) {
        return restClient.get()
                .uri("/ledger/invoices/{invoiceId}", invoiceId)
                .accept(MediaType.APPLICATION_JSON)
                .retrieve()
                .onStatus(HttpStatusCode::is5xxServerError, (request, response) -> {
                    throw new LedgerUnavailableException("Ledger service is temporarily unavailable");
                })
                .body(InvoiceStatusRecord.class);
    }

    public void acknowledgeInvoice(String invoiceId) {
        restClient.post()
                .uri("/ledger/invoices/{invoiceId}/acknowledgements", invoiceId)
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.APPLICATION_JSON)
                .body(Map.of("source", "billing-bridge"))
                .retrieve()
                .toBodilessEntity();
    }
}
EOF

mvn -q test
