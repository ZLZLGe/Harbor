package com.example.warehouse.model;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.Id;
import javax.persistence.Table;

@Entity
@Table(name = "warehouse_docks")
public class WarehouseDock {
    @Id
    private Long id;

    @Column(nullable = false, unique = true)
    private String code;
}
