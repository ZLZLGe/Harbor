package com.example.billing.job;

import java.util.List;

public record ArchiveSummary(int archivedCount, int auditCount, List<String> archivedInvoiceNumbers) {
}
