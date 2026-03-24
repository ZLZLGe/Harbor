package com.example.reporting.client;

public record ArchiveImportReceipt(
    String confirmationId,
    String status,
    String acceptedAt
) {
}
