package com.acme.reconcile.persistence;

import com.acme.reconcile.model.BatchStatus;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Set;

public record ReconciliationSearchFilter(
        Set<BatchStatus> statuses,
        String currency,
        LocalDate batchDateFrom,
        LocalDate batchDateTo,
        BigDecimal minimumVariance,
        Boolean escalatedOnly,
        String term) {
}
