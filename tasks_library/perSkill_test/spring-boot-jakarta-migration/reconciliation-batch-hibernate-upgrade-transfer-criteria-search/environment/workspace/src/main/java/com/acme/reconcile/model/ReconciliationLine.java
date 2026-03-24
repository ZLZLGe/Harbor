package com.acme.reconcile.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

@Entity
@Table(name = "reconciliation_line")
public class ReconciliationLine {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "batch_id", nullable = false)
    private ReconciliationBatch batch;

    @Column(nullable = false)
    private String partnerReference;

    @Column(nullable = false)
    private String statementReference;

    protected ReconciliationLine() {
    }

    public ReconciliationLine(
            ReconciliationBatch batch,
            String partnerReference,
            String statementReference) {
        this.batch = batch;
        this.partnerReference = partnerReference;
        this.statementReference = statementReference;
    }

    public Long getId() {
        return id;
    }

    public ReconciliationBatch getBatch() {
        return batch;
    }

    public String getPartnerReference() {
        return partnerReference;
    }

    public String getStatementReference() {
        return statementReference;
    }
}
