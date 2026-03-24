package com.example.reconciliation.client;

public record LedgerAckResponse(
    String batchId,
    int acceptedCount
) {
}
