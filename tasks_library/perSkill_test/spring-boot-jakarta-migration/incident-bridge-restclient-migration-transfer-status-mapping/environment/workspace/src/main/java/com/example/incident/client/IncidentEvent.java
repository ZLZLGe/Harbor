package com.example.incident.client;

public record IncidentEvent(
    String incidentId,
    String serviceName,
    String severity,
    String summary
) {
}
