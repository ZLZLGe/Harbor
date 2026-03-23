package com.example.billingbridge.dto;

public record InvoiceStatusRecord(
        String invoiceId,
        String state,
        String owner,
        boolean overdue) {
}
