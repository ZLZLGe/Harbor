package com.harbor.pluginmanifest.steps;

import com.harbor.pluginmanifest.model.ManifestStep;
import com.harbor.pluginmanifest.model.StepSummary;
import java.util.LinkedHashMap;
import java.util.Map;

public final class CopyAssetStep implements ManifestStep {
  private String source;
  private String destination;

  public String getSource() {
    return source;
  }

  public void setSource(String source) {
    this.source = source;
  }

  public String getDestination() {
    return destination;
  }

  public void setDestination(String destination) {
    this.destination = destination;
  }

  @Override
  public StepSummary materialize() {
    Map<String, String> details = new LinkedHashMap<>();
    details.put("source", source);
    details.put("destination", destination);
    return new StepSummary("copyAsset", details);
  }
}
