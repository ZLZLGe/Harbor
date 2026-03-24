package com.acme.logistics.model;

import com.fasterxml.jackson.databind.JsonNode;
import io.hypersistence.utils.hibernate.type.json.JsonBinaryType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import org.hibernate.annotations.Type;
import org.hibernate.annotations.TypeDef;

@Entity
@Table(name = "shipment_events")
@TypeDef(name = "jsonb", typeClass = JsonBinaryType.class)
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

    @Type(type = "jsonb")
    @Column(name = "metadata", nullable = false, columnDefinition = "jsonb")
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
