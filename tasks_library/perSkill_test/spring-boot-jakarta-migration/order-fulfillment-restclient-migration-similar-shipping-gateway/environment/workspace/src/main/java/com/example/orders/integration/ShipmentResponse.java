package com.example.orders.integration;

public record ShipmentResponse(
    String shipmentId,
    String labelUrl,
    String status
) {
}
