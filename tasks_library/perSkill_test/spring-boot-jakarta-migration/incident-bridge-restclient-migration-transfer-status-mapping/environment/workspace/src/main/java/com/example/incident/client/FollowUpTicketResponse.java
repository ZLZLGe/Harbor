package com.example.incident.client;

public record FollowUpTicketResponse(
    String ticketId,
    String status
) {
}
