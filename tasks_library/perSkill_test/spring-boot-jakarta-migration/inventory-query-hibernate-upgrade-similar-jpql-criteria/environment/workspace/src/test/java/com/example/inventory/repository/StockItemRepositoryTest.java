package com.example.inventory.repository;

import static org.assertj.core.api.Assertions.assertThat;

import com.example.inventory.model.StockItem;
import java.time.LocalDateTime;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;

@DataJpaTest
class StockItemRepositoryTest {

    @Autowired
    private StockItemRepository stockItemRepository;

    @Autowired
    private TestEntityManager entityManager;

    @BeforeEach
    void setUp() {
        stockItemRepository.deleteAll();
        stockItemRepository.saveAll(
            List.of(
                item("AXLE-14", "Axle Assembly", "Drivetrain", "WH-EAST", 14, true),
                item("BOLT-09", "Hex Bolt", "Hardware", "WH-EAST", 9, true),
                item("NUT-11", "Lock Nut", "Hardware", "WH-EAST", 11, true),
                item("BOLT-25", "Bolt Kit", "Hardware", "WH-EAST", 25, true),
                item("BOLT-30", "Hex Bolt", "Hardware", "WH-EAST", 30, false),
                item("MASK-07", "Paint Mask", "Safety", "WH-WEST", 7, true)
            )
        );
        entityManager.flush();
        entityManager.clear();
    }

    @Test
    void searchFiltersActiveWarehouseMatchesCaseInsensitiveCategoryAndSorts() {
        List<StockItem> matches = stockItemRepository.searchActiveItems("WH-EAST", "hardware", 10);

        assertThat(matches)
            .extracting(StockItem::getSku)
            .containsExactly("NUT-11", "BOLT-25");
    }

    @Test
    void searchWithBlankTermReturnsOnlyActiveItemsForWarehouseOrderedByQuantityThenSku() {
        List<StockItem> matches = stockItemRepository.searchActiveItems("WH-EAST", "   ", null);

        assertThat(matches)
            .extracting(StockItem::getSku)
            .containsExactly("BOLT-09", "NUT-11", "AXLE-14", "BOLT-25");
    }

    @Test
    void deactivateLowStockItemsOnlyUpdatesMatchingActiveRows() {
        int updated = stockItemRepository.deactivateLowStockItems("WH-EAST", 10);

        entityManager.flush();
        entityManager.clear();

        assertThat(updated).isEqualTo(1);
        assertThat(stockItemRepository.findBySku("BOLT-09")).get().extracting(StockItem::isActive).isEqualTo(false);
        assertThat(stockItemRepository.findBySku("BOLT-30")).get().extracting(StockItem::isActive).isEqualTo(false);
        assertThat(stockItemRepository.findBySku("MASK-07")).get().extracting(StockItem::isActive).isEqualTo(true);
        assertThat(stockItemRepository.findBySku("NUT-11")).get().extracting(StockItem::isActive).isEqualTo(true);
    }

    private StockItem item(String sku, String name, String category, String warehouseCode, int quantity, boolean active) {
        return new StockItem(
            sku,
            name,
            category,
            warehouseCode,
            quantity,
            active,
            LocalDateTime.of(2024, 1, 1, 10, 0)
        );
    }
}
