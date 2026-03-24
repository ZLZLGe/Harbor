package com.example.reconciliation.client;

import java.util.List;

public record LedgerConfirmationBatch(
    String reconciliationRunId,
    List<LedgerConfirmation> confirmations
) {
}
