package com.acme.platform.ops;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public final class HealthReportPrinter {
    private static final Logger LOGGER = LoggerFactory.getLogger(HealthReportPrinter.class);
    private final ObjectMapper mapper = new ObjectMapper();

    public String render(String service, boolean healthy) {
        try {
            String json = mapper.writeValueAsString(new HealthReport(service, healthy));
            LOGGER.info("Rendered report for {}", service);
            return json;
        } catch (Exception exception) {
            throw new IllegalStateException("Unable to render health report", exception);
        }
    }

    private static final class HealthReport {
        private final String service;
        private final boolean healthy;

        private HealthReport(String service, boolean healthy) {
            this.service = service;
            this.healthy = healthy;
        }

        @JsonProperty("service")
        public String getService() {
            return service;
        }

        @JsonProperty("healthy")
        public boolean isHealthy() {
            return healthy;
        }
    }
}
