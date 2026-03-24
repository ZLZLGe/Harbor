package com.harbor.pluginmanifest.steps;

import com.harbor.pluginmanifest.model.ManifestStep;
import com.harbor.pluginmanifest.model.StepSummary;
import java.util.LinkedHashMap;
import java.util.Map;

public final class RegisterWebhookStep implements ManifestStep {
  private String endpoint;
  private String event;

  public String getEndpoint() {
    return endpoint;
  }

  public void setEndpoint(String endpoint) {
    this.endpoint = endpoint;
  }

  public String getEvent() {
    return event;
  }

  public void setEvent(String event) {
    this.event = event;
  }

  @Override
  public StepSummary materialize() {
    Map<String, String> details = new LinkedHashMap<>();
    details.put("endpoint", endpoint);
    details.put("event", event);
    return new StepSummary("registerWebhook", details);
  }
}
