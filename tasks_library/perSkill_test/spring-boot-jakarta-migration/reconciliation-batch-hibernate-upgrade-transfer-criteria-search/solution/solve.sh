#!/bin/bash

set -euo pipefail

cd /workspace

cat <<'EOF' > src/main/java/com/acme/reconcile/persistence/ReconciliationSearchRepository.java
package com.acme.reconcile.persistence;

import com.acme.reconcile.model.ReconciliationBatch;
import com.acme.reconcile.model.ReconciliationLine;
import jakarta.persistence.EntityManager;
import jakarta.persistence.Tuple;
import jakarta.persistence.criteria.CriteriaBuilder;
import jakarta.persistence.criteria.CriteriaQuery;
import jakarta.persistence.criteria.Expression;
import jakarta.persistence.criteria.Predicate;
import jakarta.persistence.criteria.Root;
import jakarta.persistence.criteria.Subquery;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Repository;

@Repository
public class ReconciliationSearchRepository {

    private final EntityManager entityManager;

    public ReconciliationSearchRepository(EntityManager entityManager) {
        this.entityManager = entityManager;
    }

    public Page<ReconciliationBatch> search(ReconciliationSearchFilter filter, Pageable pageable) {
        CriteriaBuilder criteriaBuilder = entityManager.getCriteriaBuilder();

        CriteriaQuery<ReconciliationBatch> contentQuery = criteriaBuilder.createQuery(ReconciliationBatch.class);
        Root<ReconciliationBatch> contentRoot = contentQuery.from(ReconciliationBatch.class);
        List<Predicate> predicates = buildPredicates(filter, criteriaBuilder, contentQuery, contentRoot);
        contentQuery.select(contentRoot)
                .where(predicates.toArray(Predicate[]::new))
                .orderBy(
                        criteriaBuilder.desc(contentRoot.<java.time.LocalDate>get("batchDate")),
                        criteriaBuilder.asc(contentRoot.<String>get("batchCode")));

        List<ReconciliationBatch> content = entityManager.createQuery(contentQuery)
                .setFirstResult((int) pageable.getOffset())
                .setMaxResults(pageable.getPageSize())
                .getResultList();

        CriteriaQuery<Long> countQuery = criteriaBuilder.createQuery(Long.class);
        Root<ReconciliationBatch> countRoot = countQuery.from(ReconciliationBatch.class);
        List<Predicate> countPredicates = buildPredicates(filter, criteriaBuilder, countQuery, countRoot);
        countQuery.select(criteriaBuilder.count(countRoot))
                .where(countPredicates.toArray(Predicate[]::new));

        long total = entityManager.createQuery(countQuery).getSingleResult();
        return new PageImpl<>(content, pageable, total);
    }

    public ReconciliationSummary summarize(ReconciliationSearchFilter filter) {
        CriteriaBuilder criteriaBuilder = entityManager.getCriteriaBuilder();
        CriteriaQuery<Tuple> summaryQuery = criteriaBuilder.createTupleQuery();
        Root<ReconciliationBatch> root = summaryQuery.from(ReconciliationBatch.class);
        List<Predicate> predicates = buildPredicates(filter, criteriaBuilder, summaryQuery, root);
        summaryQuery.multiselect(
                        criteriaBuilder.count(root),
                        criteriaBuilder.sum(root.<BigDecimal>get("varianceAmount")))
                .where(predicates.toArray(Predicate[]::new));

        Tuple tuple = entityManager.createQuery(summaryQuery).getSingleResult();
        BigDecimal totalVariance = tuple.get(1, BigDecimal.class);
        return new ReconciliationSummary(
                tuple.get(0, Long.class),
                totalVariance == null ? BigDecimal.ZERO : totalVariance);
    }

    private List<Predicate> buildPredicates(
            ReconciliationSearchFilter filter,
            CriteriaBuilder criteriaBuilder,
            CriteriaQuery<?> query,
            Root<ReconciliationBatch> root) {
        List<Predicate> predicates = new ArrayList<>();
        if (filter == null) {
            return predicates;
        }

        if (filter.statuses() != null && !filter.statuses().isEmpty()) {
            predicates.add(root.get("status").in(filter.statuses()));
        }
        if (hasText(filter.currency())) {
            predicates.add(criteriaBuilder.equal(
                    root.<String>get("currency"),
                    filter.currency().trim().toUpperCase(Locale.ROOT)));
        }
        if (filter.batchDateFrom() != null) {
            predicates.add(criteriaBuilder.greaterThanOrEqualTo(
                    root.<java.time.LocalDate>get("batchDate"),
                    filter.batchDateFrom()));
        }
        if (filter.batchDateTo() != null) {
            predicates.add(criteriaBuilder.lessThanOrEqualTo(
                    root.<java.time.LocalDate>get("batchDate"),
                    filter.batchDateTo()));
        }
        if (filter.minimumVariance() != null) {
            predicates.add(criteriaBuilder.greaterThanOrEqualTo(
                    root.<BigDecimal>get("varianceAmount"),
                    filter.minimumVariance()));
        }
        if (filter.escalatedOnly() != null) {
            predicates.add(criteriaBuilder.equal(root.<Boolean>get("escalated"), filter.escalatedOnly()));
        }
        if (hasText(filter.term())) {
            String pattern = "%" + filter.term().trim().toLowerCase(Locale.ROOT) + "%";
            predicates.add(criteriaBuilder.or(
                    likeIgnoreCase(criteriaBuilder, root.<String>get("batchCode"), pattern),
                    likeIgnoreCase(criteriaBuilder, root.<String>get("merchantName"), pattern),
                    matchingLineExists(criteriaBuilder, query, root, pattern)));
        }
        return predicates;
    }

    private Predicate matchingLineExists(
            CriteriaBuilder criteriaBuilder,
            CriteriaQuery<?> query,
            Root<ReconciliationBatch> root,
            String pattern) {
        Subquery<Long> lineQuery = query.subquery(Long.class);
        Root<ReconciliationLine> lineRoot = lineQuery.from(ReconciliationLine.class);
        lineQuery.select(criteriaBuilder.literal(1L))
                .where(
                        criteriaBuilder.equal(lineRoot.get("batch"), root),
                        criteriaBuilder.or(
                                likeIgnoreCase(criteriaBuilder, lineRoot.<String>get("partnerReference"), pattern),
                                likeIgnoreCase(criteriaBuilder, lineRoot.<String>get("statementReference"), pattern)));
        return criteriaBuilder.exists(lineQuery);
    }

    private Predicate likeIgnoreCase(
            CriteriaBuilder criteriaBuilder,
            Expression<String> expression,
            String pattern) {
        return criteriaBuilder.like(criteriaBuilder.lower(expression), pattern);
    }

    private boolean hasText(String value) {
        return value != null && !value.trim().isEmpty();
    }
}
EOF

mvn -q -DskipTests compile
mvn -q test
