package com.example.orders.integration;

import java.math.BigDecimal;

public record ShipmentRequest(
    String orderId,
    String destinationZip,
    BigDecimal weightKg
) {
}
