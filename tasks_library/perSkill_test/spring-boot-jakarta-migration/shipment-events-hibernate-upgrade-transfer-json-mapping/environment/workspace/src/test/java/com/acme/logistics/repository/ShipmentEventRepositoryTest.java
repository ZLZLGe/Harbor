package com.acme.logistics.repository;

import static org.assertj.core.api.Assertions.assertThat;

import com.acme.logistics.model.ShipmentEvent;
import com.acme.logistics.model.ShipmentEventType;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.jdbc.core.JdbcTemplate;

@DataJpaTest
class ShipmentEventRepositoryTest {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    @Autowired
    private ShipmentEventRepository repository;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Test
    void persistsNestedMetadataAsJson() {
        ObjectNode metadata = OBJECT_MAPPER.createObjectNode();
        metadata.put("facility", "HKG-HUB");
        metadata.put("carrier", "Blue Freight");
        ObjectNode temperature = metadata.putObject("temperature");
        temperature.put("value", 4);
        temperature.put("unit", "C");
        ArrayNode checkpoints = metadata.putArray("checkpoints");
        checkpoints.add("received");
        checkpoints.add("sorted");

        ShipmentEvent saved = repository.saveAndFlush(new ShipmentEvent(
                "SHIP-1001",
                ShipmentEventType.SCANNED_IN,
                Instant.parse("2025-02-01T10:15:30Z"),
                metadata));

        String storedMetadata = jdbcTemplate.queryForObject(
                "select metadata from shipment_events where id = ?",
                String.class,
                saved.getId());

        assertThat(storedMetadata).contains("\"facility\":\"HKG-HUB\"");
        assertThat(storedMetadata).contains("\"temperature\":{\"value\":4,\"unit\":\"C\"}");
        assertThat(storedMetadata).contains("\"checkpoints\":[\"received\",\"sorted\"]");
    }

    @Test
    void readsMetadataBackThroughHibernateJsonMapping() {
        ObjectNode metadata = OBJECT_MAPPER.createObjectNode();
        metadata.put("facility", "LAX-DOCK");
        ObjectNode dimensions = metadata.putObject("dimensions");
        dimensions.put("length", 40);
        dimensions.put("width", 24);
        dimensions.put("unit", "cm");
        ArrayNode flags = metadata.putArray("flags");
        flags.add("fragile");
        flags.add("priority");

        repository.saveAndFlush(new ShipmentEvent(
                "SHIP-2002",
                ShipmentEventType.OUT_FOR_DELIVERY,
                Instant.parse("2025-02-03T06:45:00Z"),
                metadata));

        List<ShipmentEvent> events = repository.findByShipmentIdOrderByOccurredAtAsc("SHIP-2002");

        assertThat(events).hasSize(1);
        assertThat(events.get(0).getMetadata().path("dimensions").path("unit").asText()).isEqualTo("cm");
        assertThat(events.get(0).getMetadata().path("dimensions").path("length").asInt()).isEqualTo(40);
        assertThat(events.get(0).getMetadata().path("flags").get(0).asText()).isEqualTo("fragile");
        assertThat(events.get(0).getMetadata().path("flags").get(1).asText()).isEqualTo("priority");
    }
}
