package com.example.billingbridge.client;

import com.example.billingbridge.dto.InvoiceStatusRecord;
import com.example.billingbridge.exception.LedgerUnavailableException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Map;

@Service
public class InvoiceLedgerClient {

    private final RestTemplate restTemplate;
    private final String baseUrl;

    public InvoiceLedgerClient(@Value("${ledger.api.base-url}") String baseUrl) {
        this.baseUrl = baseUrl;
        this.restTemplate = new RestTemplate();
    }

    public InvoiceStatusRecord fetchInvoice(String invoiceId) {
        HttpHeaders headers = new HttpHeaders();
        headers.setAccept(List.of(MediaType.APPLICATION_JSON));
        HttpEntity<Void> request = new HttpEntity<>(headers);

        try {
            ResponseEntity<InvoiceStatusRecord> response = restTemplate.exchange(
                    baseUrl + "/ledger/invoices/" + invoiceId,
                    HttpMethod.GET,
                    request,
                    InvoiceStatusRecord.class
            );
            return response.getBody();
        } catch (HttpServerErrorException ex) {
            throw new LedgerUnavailableException("Ledger service is temporarily unavailable");
        }
    }

    public void acknowledgeInvoice(String invoiceId) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setAccept(List.of(MediaType.APPLICATION_JSON));
        HttpEntity<Map<String, String>> request = new HttpEntity<>(
                Map.of("source", "billing-bridge"),
                headers
        );

        restTemplate.postForEntity(
                baseUrl + "/ledger/invoices/" + invoiceId + "/acknowledgements",
                request,
                Void.class
        );
    }
}
