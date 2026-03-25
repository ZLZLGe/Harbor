#!/bin/bash
set -euo pipefail

cd /workspace

python3 - <<'PY'
from pathlib import Path

job_path = Path("src/main/java/com/example/billing/job/InvoiceArchiveJob.java")
job_path.write_text("""package com.example.billing.job;

import com.example.billing.model.ArchiveAudit;
import com.example.billing.model.Invoice;
import com.example.billing.model.InvoiceStatus;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.criteria.CriteriaBuilder;
import jakarta.persistence.criteria.CriteriaQuery;
import jakarta.persistence.criteria.Predicate;
import jakarta.persistence.criteria.Root;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class InvoiceArchiveJob {

    @PersistenceContext
    private EntityManager entityManager;

    @Transactional
    public ArchiveSummary archiveOverdueInvoices(LocalDate businessDate) {
        CriteriaBuilder criteriaBuilder = entityManager.getCriteriaBuilder();
        CriteriaQuery<Invoice> query = criteriaBuilder.createQuery(Invoice.class);
        Root<Invoice> root = query.from(Invoice.class);

        List<Predicate> predicates = new ArrayList<>();
        predicates.add(criteriaBuilder.equal(root.get("status"), InvoiceStatus.SENT));
        predicates.add(criteriaBuilder.lessThan(root.get("dueDate"), businessDate));
        predicates.add(criteriaBuilder.isFalse(root.get("archived")));

        query.select(root)
            .where(predicates.toArray(new Predicate[0]))
            .orderBy(criteriaBuilder.asc(root.get("invoiceNumber")));

        List<Invoice> overdueInvoices = entityManager.createQuery(query).getResultList();
        if (overdueInvoices.isEmpty()) {
            return new ArchiveSummary(0, 0, List.of());
        }

        LocalDateTime archivedAt = LocalDateTime.now().withNano(0);

        int updated = entityManager.createQuery(
                "update Invoice invoice "
                    + "set invoice.archived = true, invoice.archivedAt = :archivedAt "
                    + "where invoice.status = :status and invoice.dueDate < :businessDate "
                    + "and invoice.archived = false"
            )
            .setParameter("archivedAt", archivedAt)
            .setParameter("status", InvoiceStatus.SENT)
            .setParameter("businessDate", businessDate)
            .executeUpdate();

        entityManager.flush();
        entityManager.clear();

        List<String> archivedInvoiceNumbers = overdueInvoices.stream()
            .map(Invoice::getInvoiceNumber)
            .sorted()
            .toList();

        for (String invoiceNumber : archivedInvoiceNumbers) {
            entityManager.persist(new ArchiveAudit(invoiceNumber, "OVERDUE", "billing-batch", archivedAt));
        }

        return new ArchiveSummary(updated, archivedInvoiceNumbers.size(), archivedInvoiceNumbers);
    }
}
""")

audit_path = Path("src/main/java/com/example/billing/model/ArchiveAudit.java")
audit_path.write_text("""package com.example.billing.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

@Entity
@Table(name = "archive_audits")
public class ArchiveAudit {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "invoice_number", nullable = false)
    private String invoiceNumber;

    @Column(nullable = false)
    private String reason;

    @Column(nullable = false)
    private String operator;

    @Column(name = "archived_at", nullable = false)
    private LocalDateTime archivedAt;

    protected ArchiveAudit() {
    }

    public ArchiveAudit(String invoiceNumber, String reason, String operator, LocalDateTime archivedAt) {
        this.invoiceNumber = invoiceNumber;
        this.reason = reason;
        this.operator = operator;
        this.archivedAt = archivedAt;
    }

    public Long getId() {
        return id;
    }

    public String getInvoiceNumber() {
        return invoiceNumber;
    }

    public String getReason() {
        return reason;
    }

    public String getOperator() {
        return operator;
    }

    public LocalDateTime getArchivedAt() {
        return archivedAt;
    }
}
""")
PY

mvn test -q
