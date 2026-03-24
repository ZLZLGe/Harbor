#!/bin/bash

set -euo pipefail

cd /workspace

cat <<'EOF' > src/main/java/com/acme/logistics/model/ShipmentEvent.java
package com.acme.logistics.model;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "shipment_events")
public class ShipmentEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "shipment_id", nullable = false, length = 64)
    private String shipmentId;

    @Enumerated(EnumType.STRING)
    @Column(name = "event_type", nullable = false, length = 32)
    private ShipmentEventType eventType;

    @Column(name = "occurred_at", nullable = false)
    private Instant occurredAt;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata", nullable = false)
    private JsonNode metadata;

    protected ShipmentEvent() {
    }

    public ShipmentEvent(String shipmentId, ShipmentEventType eventType, Instant occurredAt, JsonNode metadata) {
        this.shipmentId = shipmentId;
        this.eventType = eventType;
        this.occurredAt = occurredAt;
        this.metadata = metadata;
    }

    public Long getId() {
        return id;
    }

    public String getShipmentId() {
        return shipmentId;
    }

    public ShipmentEventType getEventType() {
        return eventType;
    }

    public Instant getOccurredAt() {
        return occurredAt;
    }

    public JsonNode getMetadata() {
        return metadata;
    }
}
EOF

mvn -q -DskipTests compile
mvn -q test
