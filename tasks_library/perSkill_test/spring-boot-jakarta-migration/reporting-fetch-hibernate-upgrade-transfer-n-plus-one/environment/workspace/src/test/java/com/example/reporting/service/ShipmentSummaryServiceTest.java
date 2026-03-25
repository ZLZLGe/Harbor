package com.example.reporting.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.example.reporting.model.Shipment;
import com.example.reporting.model.ShipmentStatus;
import com.example.reporting.model.Warehouse;
import jakarta.persistence.EntityManager;
import jakarta.persistence.EntityManagerFactory;
import java.time.LocalDate;
import java.util.List;
import org.hibernate.SessionFactory;
import org.hibernate.stat.Statistics;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@Transactional
class ShipmentSummaryServiceTest {

    private static final LocalDate REPORT_DATE = LocalDate.of(2025, 3, 14);

    @Autowired
    private ShipmentSummaryService shipmentSummaryService;

    @Autowired
    private EntityManager entityManager;

    @Autowired
    private EntityManagerFactory entityManagerFactory;

    private Statistics statistics;

    @BeforeEach
    void setUp() {
        statistics = entityManagerFactory.unwrap(SessionFactory.class).getStatistics();
        statistics.clear();

        entityManager.createQuery("delete from ShipmentLine").executeUpdate();
        entityManager.createQuery("delete from Shipment").executeUpdate();
        entityManager.createQuery("delete from Warehouse").executeUpdate();

        Warehouse east = new Warehouse("WH-EAST", "east");
        Warehouse west = new Warehouse("WH-WEST", "west");
        Warehouse north = new Warehouse("WH-NORTH", "north");
        Warehouse spare = new Warehouse("WH-SPARE", "south");

        entityManager.persist(east);
        entityManager.persist(west);
        entityManager.persist(north);
        entityManager.persist(spare);

        Shipment alpha = new Shipment("SHP-100", "Atlas Stores", REPORT_DATE, ShipmentStatus.IN_TRANSIT, true, east);
        alpha.addLine("SKU-ALPHA-1", 2, 4);
        alpha.addLine("SKU-ALPHA-2", 1, 6);

        Shipment beta = new Shipment("SHP-101", "Beacon Retail", REPORT_DATE, ShipmentStatus.DELIVERED, false, west);
        beta.addLine("SKU-BETA-1", 1, 4);
        beta.addLine("SKU-BETA-2", 2, 6);
        beta.addLine("SKU-BETA-3", 1, 1);

        Shipment gamma = new Shipment("SHP-102", "Crate Hub", REPORT_DATE, ShipmentStatus.DELIVERED, true, north);
        gamma.addLine("SKU-GAMMA-1", 3, 8);

        Shipment wrongDate = new Shipment("SHP-103", "Delayed Shop", REPORT_DATE.minusDays(1), ShipmentStatus.DELIVERED, false, spare);
        wrongDate.addLine("SKU-OLD-1", 1, 5);

        Shipment wrongStatus = new Shipment("SHP-104", "Plan Only", REPORT_DATE, ShipmentStatus.PLANNED, false, spare);
        wrongStatus.addLine("SKU-PLAN-1", 1, 9);

        entityManager.persist(alpha);
        entityManager.persist(beta);
        entityManager.persist(gamma);
        entityManager.persist(wrongDate);
        entityManager.persist(wrongStatus);

        entityManager.flush();
        entityManager.clear();
        statistics.clear();
    }

    @Test
    void loadDailyShipmentSummaries_returnsUniqueRowsWithCorrectAggregates() {
        List<ShipmentSummary> summaries = shipmentSummaryService.loadDailyShipmentSummaries(REPORT_DATE);

        assertThat(summaries)
            .extracting(ShipmentSummary::referenceNumber)
            .containsExactly("SHP-100", "SHP-101", "SHP-102");

        assertThat(summaries)
            .extracting(ShipmentSummary::warehouseCode)
            .containsExactly("WH-EAST", "WH-WEST", "WH-NORTH");

        assertThat(summaries)
            .extracting(ShipmentSummary::customerName)
            .containsExactly("Atlas Stores", "Beacon Retail", "Crate Hub");

        assertThat(summaries)
            .extracting(ShipmentSummary::lineCount)
            .containsExactly(2L, 3L, 1L);

        assertThat(summaries)
            .extracting(ShipmentSummary::totalUnits)
            .containsExactly(10, 11, 8);

        assertThat(summaries)
            .extracting(ShipmentSummary::priority)
            .containsExactly(true, false, true);
    }

    @Test
    void loadDailyShipmentSummaries_usesNoMoreThanTwoPreparedStatements() {
        List<ShipmentSummary> summaries = shipmentSummaryService.loadDailyShipmentSummaries(REPORT_DATE);

        assertThat(summaries).hasSize(3);
        assertThat(statistics.getPrepareStatementCount()).isLessThanOrEqualTo(2L);
    }
}
