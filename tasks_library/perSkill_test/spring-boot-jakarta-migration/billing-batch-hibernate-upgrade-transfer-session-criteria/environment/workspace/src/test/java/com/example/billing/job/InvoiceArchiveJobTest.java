package com.example.billing.job;

import com.example.billing.model.ArchiveAudit;
import com.example.billing.model.Invoice;
import com.example.billing.model.InvoiceStatus;
import jakarta.persistence.EntityManager;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@Transactional
class InvoiceArchiveJobTest {

    @Autowired
    private EntityManager entityManager;

    @Autowired
    private InvoiceArchiveJob invoiceArchiveJob;

    @BeforeEach
    void setUp() {
        entityManager.createQuery("delete from ArchiveAudit").executeUpdate();
        entityManager.createQuery("delete from Invoice").executeUpdate();

        persistInvoice("INV-100", InvoiceStatus.SENT, LocalDate.of(2024, 1, 12), "180.00", false);
        persistInvoice("INV-101", InvoiceStatus.SENT, LocalDate.of(2024, 1, 14), "90.00", false);
        persistInvoice("INV-200", InvoiceStatus.SENT, LocalDate.of(2024, 2, 8), "75.00", false);
        persistInvoice("INV-300", InvoiceStatus.PAID, LocalDate.of(2024, 1, 10), "40.00", false);
        persistInvoice("INV-400", InvoiceStatus.SENT, LocalDate.of(2024, 1, 5), "125.00", true);
        entityManager.flush();
        entityManager.clear();
    }

    @Test
    void archivesOnlyOverdueSentInvoicesAndWritesAuditRows() {
        ArchiveSummary summary = invoiceArchiveJob.archiveOverdueInvoices(LocalDate.of(2024, 2, 1));
        entityManager.flush();
        entityManager.clear();

        assertThat(summary.archivedCount()).isEqualTo(2);
        assertThat(summary.auditCount()).isEqualTo(2);
        assertThat(summary.archivedInvoiceNumbers()).containsExactly("INV-100", "INV-101");

        List<Invoice> invoices = entityManager.createQuery(
            "select i from Invoice i order by i.invoiceNumber",
            Invoice.class
        ).getResultList();

        Invoice inv100 = invoices.get(0);
        Invoice inv101 = invoices.get(1);
        Invoice inv200 = invoices.get(2);
        Invoice inv300 = invoices.get(3);
        Invoice inv400 = invoices.get(4);

        assertThat(inv100.isArchived()).isTrue();
        assertThat(inv101.isArchived()).isTrue();
        assertThat(inv100.getArchivedAt()).isNotNull();
        assertThat(inv101.getArchivedAt()).isEqualTo(inv100.getArchivedAt());
        assertThat(inv200.isArchived()).isFalse();
        assertThat(inv300.isArchived()).isFalse();
        assertThat(inv400.isArchived()).isTrue();

        List<ArchiveAudit> audits = entityManager.createQuery(
            "select a from ArchiveAudit a order by a.invoiceNumber",
            ArchiveAudit.class
        ).getResultList();

        assertThat(audits).hasSize(2);
        assertThat(audits).extracting(ArchiveAudit::getInvoiceNumber).containsExactly("INV-100", "INV-101");
        assertThat(audits).extracting(ArchiveAudit::getReason).containsOnly("OVERDUE");
        assertThat(audits).extracting(ArchiveAudit::getOperator).containsOnly("billing-batch");
        assertThat(audits).extracting(ArchiveAudit::getArchivedAt).containsOnly(inv100.getArchivedAt());
    }

    @Test
    void returnsEmptySummaryWhenNoInvoicesMatch() {
        ArchiveSummary summary = invoiceArchiveJob.archiveOverdueInvoices(LocalDate.of(2024, 1, 1));
        entityManager.flush();
        entityManager.clear();

        assertThat(summary.archivedCount()).isZero();
        assertThat(summary.auditCount()).isZero();
        assertThat(summary.archivedInvoiceNumbers()).isEmpty();

        Long auditCount = entityManager.createQuery(
            "select count(a) from ArchiveAudit a",
            Long.class
        ).getSingleResult();
        assertThat(auditCount).isZero();
    }

    private void persistInvoice(String invoiceNumber, InvoiceStatus status, LocalDate dueDate, String amount, boolean archived) {
        entityManager.persist(new Invoice(
            invoiceNumber,
            status,
            dueDate,
            new BigDecimal(amount),
            archived
        ));
    }
}
