package com.example.billing.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import org.hibernate.annotations.GenericGenerator;

@Entity
@Table(name = "archive_audits")
public class ArchiveAudit {

    @Id
    @GeneratedValue(generator = "audit-increment")
    @GenericGenerator(name = "audit-increment", strategy = "increment")
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
