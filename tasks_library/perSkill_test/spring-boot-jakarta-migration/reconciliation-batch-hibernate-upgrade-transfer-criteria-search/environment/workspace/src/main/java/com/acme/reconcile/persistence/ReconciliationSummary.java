package com.acme.reconcile.persistence;

import java.math.BigDecimal;

public record ReconciliationSummary(long batchCount, BigDecimal totalVariance) {
}
