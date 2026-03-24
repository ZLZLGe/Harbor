package com.acme.reconcile.model;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "reconciliation_batch")
public class ReconciliationBatch {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String batchCode;

    @Column(nullable = false)
    private String merchantName;

    @Column(nullable = false, length = 3)
    private String currency;

    @Column(nullable = false)
    private LocalDate batchDate;

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal varianceAmount;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private BatchStatus status;

    @Column(nullable = false)
    private boolean escalated;

    @OneToMany(mappedBy = "batch", cascade = CascadeType.ALL, orphanRemoval = true)
    private final List<ReconciliationLine> lines = new ArrayList<>();

    protected ReconciliationBatch() {
    }

    public ReconciliationBatch(
            String batchCode,
            String merchantName,
            String currency,
            LocalDate batchDate,
            BigDecimal varianceAmount,
            BatchStatus status,
            boolean escalated) {
        this.batchCode = batchCode;
        this.merchantName = merchantName;
        this.currency = currency;
        this.batchDate = batchDate;
        this.varianceAmount = varianceAmount;
        this.status = status;
        this.escalated = escalated;
    }

    public void addLine(String partnerReference, String statementReference) {
        lines.add(new ReconciliationLine(this, partnerReference, statementReference));
    }

    public Long getId() {
        return id;
    }

    public String getBatchCode() {
        return batchCode;
    }

    public String getMerchantName() {
        return merchantName;
    }

    public String getCurrency() {
        return currency;
    }

    public LocalDate getBatchDate() {
        return batchDate;
    }

    public BigDecimal getVarianceAmount() {
        return varianceAmount;
    }

    public BatchStatus getStatus() {
        return status;
    }

    public boolean isEscalated() {
        return escalated;
    }

    public List<ReconciliationLine> getLines() {
        return lines;
    }
}
