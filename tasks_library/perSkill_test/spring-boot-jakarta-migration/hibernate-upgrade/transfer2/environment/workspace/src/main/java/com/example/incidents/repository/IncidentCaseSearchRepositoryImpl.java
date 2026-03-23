package com.example.incidents.repository;

import com.example.incidents.model.IncidentCase;
import java.util.List;
import javax.persistence.EntityManager;
import org.hibernate.Criteria;
import org.hibernate.Session;
import org.hibernate.criterion.Order;
import org.hibernate.criterion.Restrictions;

public class IncidentCaseSearchRepositoryImpl implements IncidentCaseSearchRepository {
    private final EntityManager entityManager;

    public IncidentCaseSearchRepositoryImpl(EntityManager entityManager) {
        this.entityManager = entityManager;
    }

    @Override
    public List<IncidentCase> findOpenCasesByTeam(String ownerTeam) {
        Session session = entityManager.unwrap(Session.class);
        Criteria criteria = session.createCriteria(IncidentCase.class);
        criteria.add(Restrictions.eq("ownerTeam", ownerTeam));
        criteria.add(Restrictions.eq("open", true));
        criteria.addOrder(Order.desc("severity"));
        return criteria.list();
    }
}
