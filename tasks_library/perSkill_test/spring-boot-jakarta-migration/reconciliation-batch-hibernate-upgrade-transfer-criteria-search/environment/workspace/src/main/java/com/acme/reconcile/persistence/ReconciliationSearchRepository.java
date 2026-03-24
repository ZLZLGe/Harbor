package com.acme.reconcile.persistence;

import com.acme.reconcile.model.ReconciliationBatch;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import org.hibernate.Criteria;
import org.hibernate.Session;
import org.hibernate.criterion.CriteriaSpecification;
import org.hibernate.criterion.MatchMode;
import org.hibernate.criterion.Order;
import org.hibernate.criterion.Projections;
import org.hibernate.criterion.Restrictions;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Repository;

@Repository
public class ReconciliationSearchRepository {

    private final jakarta.persistence.EntityManager entityManager;

    public ReconciliationSearchRepository(jakarta.persistence.EntityManager entityManager) {
        this.entityManager = entityManager;
    }

    @SuppressWarnings("unchecked")
    public Page<ReconciliationBatch> search(ReconciliationSearchFilter filter, Pageable pageable) {
        Session session = entityManager.unwrap(Session.class);

        Criteria criteria = session.createCriteria(ReconciliationBatch.class, "batch");
        criteria.createAlias("lines", "line", CriteriaSpecification.LEFT_JOIN);
        criteria.setResultTransformer(CriteriaSpecification.DISTINCT_ROOT_ENTITY);
        applyFilters(filter, criteria);
        criteria.addOrder(Order.desc("batchDate"));
        criteria.addOrder(Order.asc("batchCode"));
        criteria.setFirstResult((int) pageable.getOffset());
        criteria.setMaxResults(pageable.getPageSize());

        List<ReconciliationBatch> content = criteria.list();

        Criteria countCriteria = session.createCriteria(ReconciliationBatch.class, "batch");
        countCriteria.createAlias("lines", "line", CriteriaSpecification.LEFT_JOIN);
        applyFilters(filter, countCriteria);
        countCriteria.setProjection(Projections.countDistinct("id"));
        Long total = (Long) countCriteria.uniqueResult();

        return new PageImpl<>(content, pageable, total);
    }

    public ReconciliationSummary summarize(ReconciliationSearchFilter filter) {
        Session session = entityManager.unwrap(Session.class);

        Criteria summaryCriteria = session.createCriteria(ReconciliationBatch.class, "batch");
        summaryCriteria.createAlias("lines", "line", CriteriaSpecification.LEFT_JOIN);
        applyFilters(filter, summaryCriteria);
        summaryCriteria.setProjection(
                Projections.projectionList()
                        .add(Projections.countDistinct("id"))
                        .add(Projections.sum("varianceAmount")));

        Object[] row = (Object[]) summaryCriteria.uniqueResult();
        Long count = row == null ? 0L : (Long) row[0];
        BigDecimal totalVariance = row == null ? BigDecimal.ZERO : (BigDecimal) row[1];
        return new ReconciliationSummary(count, totalVariance == null ? BigDecimal.ZERO : totalVariance);
    }

    private void applyFilters(ReconciliationSearchFilter filter, Criteria criteria) {
        if (filter == null) {
            return;
        }

        if (filter.statuses() != null && !filter.statuses().isEmpty()) {
            criteria.add(Restrictions.in("status", new ArrayList<>(filter.statuses())));
        }
        if (hasText(filter.currency())) {
            criteria.add(Restrictions.eq("currency", filter.currency().trim().toUpperCase()));
        }
        if (filter.batchDateFrom() != null) {
            criteria.add(Restrictions.ge("batchDate", filter.batchDateFrom()));
        }
        if (filter.batchDateTo() != null) {
            criteria.add(Restrictions.le("batchDate", filter.batchDateTo()));
        }
        if (filter.minimumVariance() != null) {
            criteria.add(Restrictions.ge("varianceAmount", filter.minimumVariance()));
        }
        if (filter.escalatedOnly() != null) {
            criteria.add(Restrictions.eq("escalated", filter.escalatedOnly()));
        }
        if (hasText(filter.term())) {
            criteria.add(Restrictions.or(
                    Restrictions.ilike("batchCode", filter.term(), MatchMode.ANYWHERE),
                    Restrictions.ilike("merchantName", filter.term(), MatchMode.ANYWHERE),
                    Restrictions.ilike("line.partnerReference", filter.term(), MatchMode.ANYWHERE),
                    Restrictions.ilike("line.statementReference", filter.term(), MatchMode.ANYWHERE)));
        }
    }

    private boolean hasText(String value) {
        return value != null && !value.trim().isEmpty();
    }
}
