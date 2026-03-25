package com.example.reporting.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

@Entity
@Table(name = "shipment_line")
public class ShipmentLine {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "shipment_id", nullable = false)
    private Shipment shipment;

    @Column(nullable = false)
    private String sku;

    @Column(nullable = false)
    private int cartons;

    @Column(nullable = false)
    private int units;

    protected ShipmentLine() {
    }

    public ShipmentLine(Shipment shipment, String sku, int cartons, int units) {
        this.shipment = shipment;
        this.sku = sku;
        this.cartons = cartons;
        this.units = units;
    }

    public Long getId() {
        return id;
    }

    public Shipment getShipment() {
        return shipment;
    }

    public String getSku() {
        return sku;
    }

    public int getCartons() {
        return cartons;
    }

    public int getUnits() {
        return units;
    }
}
