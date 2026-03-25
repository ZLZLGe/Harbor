package com.example.reporting.model;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "shipment")
public class Shipment {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "reference_number", nullable = false, unique = true)
    private String referenceNumber;

    @Column(name = "customer_name", nullable = false)
    private String customerName;

    @Column(name = "departure_date", nullable = false)
    private LocalDate departureDate;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private ShipmentStatus status;

    @Column(nullable = false)
    private boolean priority;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "warehouse_id", nullable = false)
    private Warehouse warehouse;

    @OneToMany(mappedBy = "shipment", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<ShipmentLine> lines = new ArrayList<>();

    protected Shipment() {
    }

    public Shipment(
        String referenceNumber,
        String customerName,
        LocalDate departureDate,
        ShipmentStatus status,
        boolean priority,
        Warehouse warehouse
    ) {
        this.referenceNumber = referenceNumber;
        this.customerName = customerName;
        this.departureDate = departureDate;
        this.status = status;
        this.priority = priority;
        this.warehouse = warehouse;
    }

    public void addLine(String sku, int cartons, int units) {
        lines.add(new ShipmentLine(this, sku, cartons, units));
    }

    public Long getId() {
        return id;
    }

    public String getReferenceNumber() {
        return referenceNumber;
    }

    public String getCustomerName() {
        return customerName;
    }

    public LocalDate getDepartureDate() {
        return departureDate;
    }

    public ShipmentStatus getStatus() {
        return status;
    }

    public boolean isPriority() {
        return priority;
    }

    public Warehouse getWarehouse() {
        return warehouse;
    }

    public List<ShipmentLine> getLines() {
        return lines;
    }
}
