package com.example.reconciliation.client;

import java.time.LocalDate;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

@Service
public class LedgerSyncClient {

    private final RestTemplate restTemplate;
    private final String baseUrl;

    public LedgerSyncClient(
        @Value("${ledger.api.base-url:http://ledger.example.internal}") String baseUrl
    ) {
        this.baseUrl = baseUrl;
        this.restTemplate = new RestTemplate();
    }

    public PageEnvelope<LedgerEntry> fetchEntries(String cursor, int limit, LocalDate ledgerDate) {
        HttpEntity<Void> request = new HttpEntity<>(acceptHeaders());
        UriComponentsBuilder uriBuilder = UriComponentsBuilder.fromHttpUrl(baseUrl + "/ledger/entries")
            .queryParam("limit", limit)
            .queryParam("ledgerDate", ledgerDate);
        if (cursor != null && !cursor.isBlank()) {
            uriBuilder.queryParam("cursor", cursor);
        }

        ResponseEntity<PageEnvelope<LedgerEntry>> response = restTemplate.exchange(
            uriBuilder.toUriString(),
            HttpMethod.GET,
            request,
            new ParameterizedTypeReference<PageEnvelope<LedgerEntry>>() {
            }
        );
        return response.getBody();
    }

    public LedgerAckResponse submitConfirmations(LedgerConfirmationBatch batch) {
        HttpEntity<LedgerConfirmationBatch> request = new HttpEntity<>(batch, jsonHeaders());
        ResponseEntity<LedgerAckResponse> response = restTemplate.exchange(
            baseUrl + "/ledger/entries/confirmations",
            HttpMethod.POST,
            request,
            LedgerAckResponse.class
        );
        return response.getBody();
    }

    private HttpHeaders acceptHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.setAccept(List.of(MediaType.APPLICATION_JSON));
        return headers;
    }

    private HttpHeaders jsonHeaders() {
        HttpHeaders headers = acceptHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        return headers;
    }
}
