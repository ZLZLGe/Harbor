#!/bin/bash
set -euo pipefail

cd /workspace

cat > src/main/java/com/example/compliancearchive/config/ComplianceRestClientConfig.java <<'EOF'
package com.example.compliancearchive.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;

@Configuration
public class ComplianceRestClientConfig {

    @Bean
    public RestClient complianceRestClient(@Value("${compliance.api.base-url}") String baseUrl) {
        return RestClient.builder()
                .baseUrl(baseUrl)
                .defaultHeader(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
                .defaultHeader("X-Compliance-Source", "case-ops")
                .build();
    }
}
EOF

cat > src/main/java/com/example/compliancearchive/client/ComplianceArchiveClient.java <<'EOF'
package com.example.compliancearchive.client;

import com.example.compliancearchive.dto.ArchiveReceipt;
import com.example.compliancearchive.dto.ArchiveRequest;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
public class ComplianceArchiveClient {

    private final RestClient restClient;

    public ComplianceArchiveClient(RestClient complianceRestClient) {
        this.restClient = complianceRestClient;
    }

    public ArchiveReceipt archiveCase(String caseId, String requestedBy) {
        return restClient.post()
                .uri("/cases/{caseId}/archive", caseId)
                .contentType(MediaType.APPLICATION_JSON)
                .body(new ArchiveRequest(requestedBy))
                .retrieve()
                .body(ArchiveReceipt.class);
    }

    public ArchiveReceipt fetchStatus(String caseId) {
        return restClient.get()
                .uri("/cases/{caseId}/archive-status", caseId)
                .retrieve()
                .body(ArchiveReceipt.class);
    }
}
EOF

mvn -q test
