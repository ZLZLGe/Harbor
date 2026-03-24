package com.harbor.pluginmanifest.model;

import java.util.LinkedHashMap;
import java.util.Map;

public final class StepSummary {
  private String kind;
  private Map<String, String> details = new LinkedHashMap<>();

  public StepSummary() {
  }

  public StepSummary(String kind, Map<String, String> details) {
    this.kind = kind;
    this.details = details;
  }

  public String getKind() {
    return kind;
  }

  public void setKind(String kind) {
    this.kind = kind;
  }

  public Map<String, String> getDetails() {
    return details;
  }

  public void setDetails(Map<String, String> details) {
    this.details = details;
  }
}
