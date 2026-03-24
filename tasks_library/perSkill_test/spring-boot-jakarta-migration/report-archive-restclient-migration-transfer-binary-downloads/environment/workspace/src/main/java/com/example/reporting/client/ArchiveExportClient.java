package com.example.reporting.client;

import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

@Service
public class ArchiveExportClient {

    private static final MediaType TEXT_CSV = MediaType.parseMediaType("text/csv");

    private final RestTemplate restTemplate;
    private final String baseUrl;

    public ArchiveExportClient(
        @Value("${report.archive.base-url:https://archive.example.internal}") String baseUrl
    ) {
        this.baseUrl = baseUrl;
        this.restTemplate = new RestTemplate();
    }

    public String downloadCsv(String exportId, String apiToken) {
        HttpHeaders headers = authHeaders(apiToken);
        headers.setAccept(List.of(TEXT_CSV));
        ResponseEntity<String> response = restTemplate.exchange(
            baseUrl + "/archive/exports/{exportId}/csv",
            HttpMethod.GET,
            new HttpEntity<Void>(headers),
            String.class,
            exportId
        );
        return response.getBody();
    }

    public byte[] downloadPdf(String exportId, String apiToken) {
        HttpHeaders headers = authHeaders(apiToken);
        headers.setAccept(List.of(MediaType.APPLICATION_PDF));
        ResponseEntity<byte[]> response = restTemplate.exchange(
            baseUrl + "/archive/exports/{exportId}/pdf",
            HttpMethod.GET,
            new HttpEntity<Void>(headers),
            byte[].class,
            exportId
        );
        return response.getBody();
    }

    public ArchiveImportReceipt confirmImport(ArchiveImportConfirmation confirmation, String apiToken) {
        HttpEntity<ArchiveImportConfirmation> request = new HttpEntity<>(confirmation, jsonHeaders(apiToken));
        ResponseEntity<ArchiveImportReceipt> response = restTemplate.postForEntity(
            baseUrl + "/archive/import-confirmations",
            request,
            ArchiveImportReceipt.class
        );
        return response.getBody();
    }

    private HttpHeaders authHeaders(String apiToken) {
        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(apiToken);
        return headers;
    }

    private HttpHeaders jsonHeaders(String apiToken) {
        HttpHeaders headers = authHeaders(apiToken);
        headers.setAccept(List.of(MediaType.APPLICATION_JSON));
        headers.setContentType(MediaType.APPLICATION_JSON);
        return headers;
    }
}
