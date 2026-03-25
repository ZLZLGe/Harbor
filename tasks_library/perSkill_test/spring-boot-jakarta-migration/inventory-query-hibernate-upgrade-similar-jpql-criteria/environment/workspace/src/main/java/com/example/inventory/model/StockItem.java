package com.example.inventory.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

@Entity
@Table(name = "stock_items")
public class StockItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String sku;

    @Column(nullable = false)
    private String name;

    @Column(nullable = false)
    private String category;

    @Column(nullable = false)
    private String warehouseCode;

    @Column(nullable = false)
    private int quantity;

    @Column(nullable = false)
    private boolean active;

    @Column(nullable = false)
    private LocalDateTime updatedAt;

    protected StockItem() {
    }

    public StockItem(
        String sku,
        String name,
        String category,
        String warehouseCode,
        int quantity,
        boolean active,
        LocalDateTime updatedAt
    ) {
        this.sku = sku;
        this.name = name;
        this.category = category;
        this.warehouseCode = warehouseCode;
        this.quantity = quantity;
        this.active = active;
        this.updatedAt = updatedAt;
    }

    public Long getId() {
        return id;
    }

    public String getSku() {
        return sku;
    }

    public String getName() {
        return name;
    }

    public String getCategory() {
        return category;
    }

    public String getWarehouseCode() {
        return warehouseCode;
    }

    public int getQuantity() {
        return quantity;
    }

    public boolean isActive() {
        return active;
    }

    public void setActive(boolean active) {
        this.active = active;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }
}
