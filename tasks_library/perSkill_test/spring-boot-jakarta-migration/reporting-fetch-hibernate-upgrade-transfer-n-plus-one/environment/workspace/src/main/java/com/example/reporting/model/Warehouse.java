package com.example.reporting.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "warehouse")
public class Warehouse {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String code;

    @Column(nullable = false)
    private String region;

    protected Warehouse() {
    }

    public Warehouse(String code, String region) {
        this.code = code;
        this.region = region;
    }

    public Long getId() {
        return id;
    }

    public String getCode() {
        return code;
    }

    public String getRegion() {
        return region;
    }
}
