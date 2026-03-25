package com.example.reporting.service;

public record ShipmentSummary(
    String referenceNumber,
    String warehouseCode,
    String customerName,
    long lineCount,
    int totalUnits,
    boolean priority
) {
}
