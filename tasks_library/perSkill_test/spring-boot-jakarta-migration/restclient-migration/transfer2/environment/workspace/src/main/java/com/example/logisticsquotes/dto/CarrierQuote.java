package com.example.logisticsquotes.dto;

public record CarrierQuote(
        String carrierCode,
        int estimatedDays,
        long totalCents) {
}
