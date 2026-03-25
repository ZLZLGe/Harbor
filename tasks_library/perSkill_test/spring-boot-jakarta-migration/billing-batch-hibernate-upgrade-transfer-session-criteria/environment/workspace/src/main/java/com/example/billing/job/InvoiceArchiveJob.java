package com.example.billing.job;

import com.example.billing.model.ArchiveAudit;
import com.example.billing.model.Invoice;
import com.example.billing.model.InvoiceStatus;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;
import javax.persistence.EntityManager;
import javax.persistence.PersistenceContext;
import org.hibernate.Criteria;
import org.hibernate.Session;
import org.hibernate.criterion.Order;
import org.hibernate.criterion.Restrictions;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class InvoiceArchiveJob {

    @PersistenceContext
    private EntityManager entityManager;

    @Transactional
    public ArchiveSummary archiveOverdueInvoices(LocalDate businessDate) {
        Session session = entityManager.unwrap(Session.class);
        Criteria criteria = session.createCriteria(Invoice.class);
        criteria.add(Restrictions.eq("status", InvoiceStatus.SENT));
        criteria.add(Restrictions.lt("dueDate", businessDate));
        criteria.add(Restrictions.eq("archived", false));
        criteria.addOrder(Order.asc("invoiceNumber"));

        @SuppressWarnings("unchecked")
        List<Invoice> overdueInvoices = criteria.list();
        if (overdueInvoices.isEmpty()) {
            return new ArchiveSummary(0, 0, List.of());
        }

        LocalDateTime archivedAt = LocalDateTime.now().withNano(0);
        List<Long> invoiceIds = overdueInvoices.stream()
            .map(Invoice::getId)
            .collect(Collectors.toList());

        int updated = entityManager.createQuery(
                "update from Invoice invoice "
                    + "set invoice.archived = true, invoice.archivedAt = :archivedAt "
                    + "where invoice.id in :invoiceIds"
            )
            .setParameter("archivedAt", archivedAt)
            .setParameter("invoiceIds", invoiceIds)
            .executeUpdate();

        List<ArchiveAudit> audits = new ArrayList<>();
        for (Invoice invoice : overdueInvoices) {
            audits.add(new ArchiveAudit(invoice.getInvoiceNumber(), "OVERDUE", "billing-batch", archivedAt));
        }

        for (ArchiveAudit audit : audits) {
            session.save(audit);
        }

        return new ArchiveSummary(
            updated,
            audits.size(),
            overdueInvoices.stream().map(Invoice::getInvoiceNumber).collect(Collectors.toList())
        );
    }
}
