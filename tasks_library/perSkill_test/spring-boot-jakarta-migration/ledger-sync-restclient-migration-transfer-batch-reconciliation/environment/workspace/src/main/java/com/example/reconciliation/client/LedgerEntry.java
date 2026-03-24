package com.example.reconciliation.client;

import java.math.BigDecimal;

public record LedgerEntry(
    String entryId,
    BigDecimal amount,
    String currency,
    String status
) {
}
