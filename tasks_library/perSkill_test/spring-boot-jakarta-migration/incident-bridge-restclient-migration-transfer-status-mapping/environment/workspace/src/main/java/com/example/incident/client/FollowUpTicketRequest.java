package com.example.incident.client;

public record FollowUpTicketRequest(
    String incidentId,
    String assignmentGroup,
    String note
) {
}
