#!/bin/bash
set -euo pipefail

cd /workspace

cat <<'EOF' > src/main/java/com/example/inventory/repository/StockItemRepository.java
package com.example.inventory.repository;

import com.example.inventory.model.StockItem;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.criteria.CriteriaBuilder;
import jakarta.persistence.criteria.CriteriaQuery;
import jakarta.persistence.criteria.Predicate;
import jakarta.persistence.criteria.Root;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

public interface StockItemRepository extends JpaRepository<StockItem, Long>, StockItemRepositoryCustom {

    Optional<StockItem> findBySku(String sku);
}

interface StockItemRepositoryCustom {

    List<StockItem> searchActiveItems(String warehouseCode, String term, Integer minimumQuantity);

    int deactivateLowStockItems(String warehouseCode, int cutoffQuantity);
}

@Repository
class StockItemRepositoryImpl implements StockItemRepositoryCustom {

    @PersistenceContext
    private EntityManager entityManager;

    @Override
    public List<StockItem> searchActiveItems(String warehouseCode, String term, Integer minimumQuantity) {
        CriteriaBuilder criteriaBuilder = entityManager.getCriteriaBuilder();
        CriteriaQuery<StockItem> query = criteriaBuilder.createQuery(StockItem.class);
        Root<StockItem> root = query.from(StockItem.class);

        List<Predicate> predicates = new ArrayList<>();
        predicates.add(criteriaBuilder.isTrue(root.get("active")));
        predicates.add(criteriaBuilder.equal(root.get("warehouseCode"), warehouseCode));

        if (term != null && !term.isBlank()) {
            String normalizedTerm = "%" + term.strip().toLowerCase(Locale.ROOT) + "%";
            predicates.add(
                criteriaBuilder.or(
                    criteriaBuilder.like(criteriaBuilder.lower(root.get("name")), normalizedTerm),
                    criteriaBuilder.like(criteriaBuilder.lower(root.get("category")), normalizedTerm)
                )
            );
        }

        if (minimumQuantity != null) {
            predicates.add(criteriaBuilder.greaterThanOrEqualTo(root.get("quantity"), minimumQuantity));
        }

        query.select(root)
            .where(predicates.toArray(new Predicate[0]))
            .orderBy(criteriaBuilder.asc(root.get("quantity")), criteriaBuilder.asc(root.get("sku")));

        return entityManager.createQuery(query).getResultList();
    }

    @Override
    @Transactional
    public int deactivateLowStockItems(String warehouseCode, int cutoffQuantity) {
        int updated = entityManager.createQuery(
            "update StockItem item set item.active = false, item.updatedAt = :updatedAt "
                + "where item.active = true and item.warehouseCode = :warehouseCode "
                + "and item.quantity <= :cutoffQuantity"
        )
            .setParameter("updatedAt", LocalDateTime.now())
            .setParameter("warehouseCode", warehouseCode)
            .setParameter("cutoffQuantity", cutoffQuantity)
            .executeUpdate();

        entityManager.clear();
        return updated;
    }
}
EOF

mvn test -q
