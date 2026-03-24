package com.acme.reconcile.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import com.acme.reconcile.model.BatchStatus;
import com.acme.reconcile.model.ReconciliationBatch;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;
import org.springframework.context.annotation.Import;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;

@DataJpaTest
@Import(ReconciliationSearchRepository.class)
class ReconciliationSearchRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private ReconciliationSearchRepository repository;

    @BeforeEach
    void seedData() {
        persistBatch(
                "RB-1001",
                "Alpha Tools",
                "USD",
                LocalDate.of(2026, 1, 14),
                "15.25",
                BatchStatus.REVIEW,
                true,
                "ALPHA-SETTLEMENT",
                "SET-778");
        persistBatch(
                "RB-1002",
                "Alpha Logistics",
                "USD",
                LocalDate.of(2026, 1, 12),
                "4.00",
                BatchStatus.REVIEW,
                true,
                "ALPHA-LOW",
                "SET-220");
        persistBatch(
                "RB-1003",
                "Zenith Market",
                "EUR",
                LocalDate.of(2026, 1, 13),
                "27.10",
                BatchStatus.REVIEW,
                true,
                "ZEN-ALPHA",
                "SET-881");
        persistBatch(
                "RB-1004",
                "Alpha Tools",
                "USD",
                LocalDate.of(2026, 1, 15),
                "11.00",
                BatchStatus.MATCHED,
                true,
                "ALPHA-MATCHED",
                "SET-112");
        persistBatch(
                "RB-1005",
                "Redwood Alpha",
                "USD",
                LocalDate.of(2026, 1, 20),
                "42.00",
                BatchStatus.FAILED,
                true,
                "RED-441",
                "ALPHA-TRACE");
        persistBatch(
                "RB-1006",
                "Alpha Tools",
                "USD",
                LocalDate.of(2026, 2, 1),
                "60.00",
                BatchStatus.REVIEW,
                true,
                "ALPHA-FEB",
                "SET-002");
        persistBatch(
                "RB-1007",
                "Harbor Alpha",
                "USD",
                LocalDate.of(2026, 1, 16),
                "25.00",
                BatchStatus.REVIEW,
                false,
                "ALPHA-NOESC",
                "SET-553");
        persistBatch(
                "RB-1009",
                "Clearwater Imports",
                "USD",
                LocalDate.of(2026, 1, 18),
                "8.50",
                BatchStatus.REVIEW,
                true,
                "dup-one",
                "ST-190",
                "dup-two",
                "ST-191");
        persistBatch(
                "RB-1010",
                "Northern Ledger",
                "USD",
                LocalDate.of(2026, 1, 22),
                "12.75",
                BatchStatus.FAILED,
                false,
                "dup-three",
                "ST-991");
        entityManager.flush();
        entityManager.clear();
    }

    @Test
    void search_applies_all_filters_and_returns_distinct_batches() {
        ReconciliationSearchFilter filter = new ReconciliationSearchFilter(
                Set.of(BatchStatus.REVIEW, BatchStatus.FAILED),
                "USD",
                LocalDate.of(2026, 1, 1),
                LocalDate.of(2026, 1, 31),
                new BigDecimal("10.00"),
                true,
                "alpha");

        Page<ReconciliationBatch> page = repository.search(filter, PageRequest.of(0, 5));

        assertThat(page.getTotalElements()).isEqualTo(2);
        assertThat(page.getContent())
                .extracting(ReconciliationBatch::getBatchCode)
                .containsExactly("RB-1005", "RB-1001");
    }

    @Test
    void search_paginates_without_duplicate_rows_when_multiple_lines_match() {
        ReconciliationSearchFilter filter = new ReconciliationSearchFilter(
                Set.of(BatchStatus.REVIEW, BatchStatus.FAILED),
                "USD",
                null,
                null,
                null,
                null,
                "dup");

        Page<ReconciliationBatch> firstPage = repository.search(filter, PageRequest.of(0, 1));
        Page<ReconciliationBatch> secondPage = repository.search(filter, PageRequest.of(1, 1));

        assertThat(firstPage.getTotalElements()).isEqualTo(2);
        assertThat(firstPage.getContent())
                .extracting(ReconciliationBatch::getBatchCode)
                .containsExactly("RB-1010");
        assertThat(secondPage.getContent())
                .extracting(ReconciliationBatch::getBatchCode)
                .containsExactly("RB-1009");
    }

    @Test
    void summarize_uses_the_same_filter_set_as_search() {
        ReconciliationSearchFilter filter = new ReconciliationSearchFilter(
                Set.of(BatchStatus.REVIEW, BatchStatus.FAILED),
                "USD",
                LocalDate.of(2026, 1, 1),
                LocalDate.of(2026, 1, 31),
                new BigDecimal("10.00"),
                true,
                "alpha");

        ReconciliationSummary summary = repository.summarize(filter);

        assertThat(summary.batchCount()).isEqualTo(2);
        assertThat(summary.totalVariance()).isEqualByComparingTo("57.25");
    }

    private void persistBatch(
            String batchCode,
            String merchantName,
            String currency,
            LocalDate batchDate,
            String varianceAmount,
            BatchStatus status,
            boolean escalated,
            String... lineReferences) {
        ReconciliationBatch batch = new ReconciliationBatch(
                batchCode,
                merchantName,
                currency,
                batchDate,
                new BigDecimal(varianceAmount),
                status,
                escalated);
        for (int index = 0; index < lineReferences.length; index += 2) {
            batch.addLine(lineReferences[index], lineReferences[index + 1]);
        }
        entityManager.persist(batch);
    }
}
