package com.acme.platform.events;

import org.junit.Assert;
import org.junit.Test;

public class EventEnvelopeTest {
    @Test
    public void writesExpectedJson() {
        EventEnvelope envelope = new EventEnvelope();

        String json = envelope.toJson("evt-42", "billing");

        Assert.assertTrue(json.contains("\"id\":\"evt-42\""));
        Assert.assertTrue(json.contains("\"topic\":\"billing\""));
    }
}
