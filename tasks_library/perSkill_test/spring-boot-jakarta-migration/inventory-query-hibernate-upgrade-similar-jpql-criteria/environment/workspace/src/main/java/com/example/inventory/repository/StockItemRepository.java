package com.example.inventory.repository;

import com.example.inventory.model.StockItem;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import javax.persistence.EntityManager;
import javax.persistence.PersistenceContext;
import javax.persistence.Query;
import org.hibernate.Criteria;
import org.hibernate.Session;
import org.hibernate.criterion.MatchMode;
import org.hibernate.criterion.Order;
import org.hibernate.criterion.Restrictions;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

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
        Session session = entityManager.unwrap(Session.class);
        Criteria criteria = session.createCriteria(StockItem.class, "item");
        criteria.add(Restrictions.eq("active", true));
        criteria.add(Restrictions.eq("warehouseCode", warehouseCode));

        if (term != null && !term.trim().isEmpty()) {
            criteria.add(
                Restrictions.or(
                    Restrictions.ilike("name", term.trim(), MatchMode.ANYWHERE),
                    Restrictions.ilike("category", term.trim(), MatchMode.ANYWHERE)
                )
            );
        }

        if (minimumQuantity != null) {
            criteria.add(Restrictions.ge("quantity", minimumQuantity));
        }

        criteria.addOrder(Order.asc("quantity"));
        criteria.addOrder(Order.asc("sku"));
        return new ArrayList<>(criteria.list());
    }

    @Override
    public int deactivateLowStockItems(String warehouseCode, int cutoffQuantity) {
        Query query = entityManager.createQuery(
            "update from StockItem item set item.active = false, item.updatedAt = :updatedAt "
                + "where item.active = true and item.warehouseCode = :warehouseCode "
                + "and item.quantity <= :cutoffQuantity"
        );
        query.setParameter("updatedAt", LocalDateTime.now());
        query.setParameter("warehouseCode", warehouseCode);
        query.setParameter("cutoffQuantity", cutoffQuantity);
        return query.executeUpdate();
    }
}
