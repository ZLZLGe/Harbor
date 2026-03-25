#!/bin/bash
set -euo pipefail

cd /workspace

cat <<'EOF_JAVA' > src/main/java/com/example/reporting/service/ShipmentSummaryService.java
package com.example.reporting.service;

import com.example.reporting.model.Shipment;
import com.example.reporting.model.ShipmentLine;
import com.example.reporting.model.ShipmentStatus;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import java.time.LocalDate;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class ShipmentSummaryService {

    @PersistenceContext
    private EntityManager entityManager;

    public List<ShipmentSummary> loadDailyShipmentSummaries(LocalDate reportDate) {
        return entityManager.createQuery(
                "select distinct shipment "
                    + "from Shipment shipment "
                    + "join fetch shipment.warehouse "
                    + "left join fetch shipment.lines "
                    + "where shipment.departureDate = :reportDate "
                    + "and shipment.status in :statuses "
                    + "order by shipment.referenceNumber",
                Shipment.class
            )
            .setParameter("reportDate", reportDate)
            .setParameter("statuses", List.of(ShipmentStatus.IN_TRANSIT, ShipmentStatus.DELIVERED))
            .getResultList()
            .stream()
            .map(this::toSummary)
            .toList();
    }

    private ShipmentSummary toSummary(Shipment shipment) {
        long lineCount = shipment.getLines().size();
        int totalUnits = shipment.getLines().stream()
            .mapToInt(ShipmentLine::getUnits)
            .sum();

        return new ShipmentSummary(
            shipment.getReferenceNumber(),
            shipment.getWarehouse().getCode(),
            shipment.getCustomerName(),
            lineCount,
            totalUnits,
            shipment.isPriority()
        );
    }
}
EOF_JAVA

mvn test -q
