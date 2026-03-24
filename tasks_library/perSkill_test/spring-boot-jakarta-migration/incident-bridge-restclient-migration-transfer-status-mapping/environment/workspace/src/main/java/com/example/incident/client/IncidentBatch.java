package com.example.incident.client;

import java.util.List;

public record IncidentBatch(
    List<IncidentEvent> events,
    String resumeToken
) {
}
