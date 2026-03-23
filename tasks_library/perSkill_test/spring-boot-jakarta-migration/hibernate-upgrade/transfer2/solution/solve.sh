#!/bin/bash

set -euo pipefail

cd /workspace

cat > src/main/java/com/example/incidents/model/IncidentCase.java <<'EOF'
package com.example.incidents.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "incident_cases")
public class IncidentCase {
    @Id
    private Long id;

    @Column(nullable = false)
    private String ownerTeam;

    @Column(nullable = false)
    private boolean open;

    @Column(nullable = false)
    private int severity;
}
EOF

cat > src/main/java/com/example/incidents/repository/IncidentCaseSearchRepositoryImpl.java <<'EOF'
package com.example.incidents.repository;

import com.example.incidents.model.IncidentCase;
import jakarta.persistence.EntityManager;
import jakarta.persistence.criteria.CriteriaBuilder;
import jakarta.persistence.criteria.CriteriaQuery;
import jakarta.persistence.criteria.Root;
import java.util.List;

public class IncidentCaseSearchRepositoryImpl implements IncidentCaseSearchRepository {
    private final EntityManager entityManager;

    public IncidentCaseSearchRepositoryImpl(EntityManager entityManager) {
        this.entityManager = entityManager;
    }

    @Override
    public List<IncidentCase> findOpenCasesByTeam(String ownerTeam) {
        CriteriaBuilder criteriaBuilder = entityManager.getCriteriaBuilder();
        CriteriaQuery<IncidentCase> query = criteriaBuilder.createQuery(IncidentCase.class);
        Root<IncidentCase> root = query.from(IncidentCase.class);
        query.select(root)
                .where(
                        criteriaBuilder.equal(root.get("ownerTeam"), ownerTeam),
                        criteriaBuilder.isTrue(root.get("open"))
                )
                .orderBy(criteriaBuilder.desc(root.get("severity")));
        return entityManager.createQuery(query).getResultList();
    }
}
EOF

cat > /root/transfer2_criteria_migration.txt <<'EOF'
service=incident-review
replaced_api=org.hibernate.Criteria
new_api=jakarta.persistence.criteria.CriteriaBuilder
query_method=findOpenCasesByTeam
EOF
