package com.example.orders.integration;

import java.math.BigDecimal;

public record ShippingQuote(
    String serviceLevel,
    BigDecimal feeAmount,
    int estimatedDays
) {
}
