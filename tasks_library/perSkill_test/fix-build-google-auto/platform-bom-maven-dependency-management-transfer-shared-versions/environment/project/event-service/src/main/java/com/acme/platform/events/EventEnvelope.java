package com.acme.platform.events;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public final class EventEnvelope {
    private static final Logger LOGGER = LoggerFactory.getLogger(EventEnvelope.class);
    private final ObjectMapper mapper = new ObjectMapper();

    public String toJson(String id, String topic) {
        try {
            String payload = mapper.writeValueAsString(Map.of("id", id, "topic", topic));
            LOGGER.debug("Serialized event {}", id);
            return payload;
        } catch (Exception exception) {
            throw new IllegalStateException("Unable to serialize event", exception);
        }
    }
}
