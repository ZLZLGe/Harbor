package com.example.compliancearchive.client;

import com.example.compliancearchive.dto.ArchiveReceipt;
import com.example.compliancearchive.dto.ArchiveRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.List;

@Service
public class ComplianceArchiveClient {

    private final RestTemplate restTemplate;
    private final String baseUrl;

    public ComplianceArchiveClient(
            RestTemplate complianceRestTemplate,
            @Value("${compliance.api.base-url}") String baseUrl) {
        this.restTemplate = complianceRestTemplate;
        this.baseUrl = baseUrl;
    }

    public ArchiveReceipt archiveCase(String caseId, String requestedBy) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setAccept(List.of(MediaType.APPLICATION_JSON));
        headers.set("X-Compliance-Source", "case-ops");

        HttpEntity<ArchiveRequest> request = new HttpEntity<>(new ArchiveRequest(requestedBy), headers);
        return restTemplate.postForObject(
                baseUrl + "/cases/" + caseId + "/archive",
                request,
                ArchiveReceipt.class
        );
    }

    public ArchiveReceipt fetchStatus(String caseId) {
        return restTemplate.getForObject(
                baseUrl + "/cases/" + caseId + "/archive-status",
                ArchiveReceipt.class
        );
    }
}
