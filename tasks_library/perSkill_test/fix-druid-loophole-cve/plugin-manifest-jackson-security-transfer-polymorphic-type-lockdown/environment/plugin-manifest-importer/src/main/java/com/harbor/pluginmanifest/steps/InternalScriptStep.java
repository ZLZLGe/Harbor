package com.harbor.pluginmanifest.steps;

import com.harbor.pluginmanifest.model.ManifestStep;
import com.harbor.pluginmanifest.model.StepSummary;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

public final class InternalScriptStep implements ManifestStep {
  private String markerFile;
  private String scriptBody;

  public String getMarkerFile() {
    return markerFile;
  }

  public void setMarkerFile(String markerFile) {
    this.markerFile = markerFile;
  }

  public String getScriptBody() {
    return scriptBody;
  }

  public void setScriptBody(String scriptBody) {
    this.scriptBody = scriptBody;
  }

  @Override
  public StepSummary materialize() throws IOException {
    Path markerPath = Path.of(markerFile);
    if (markerPath.getParent() != null) {
      Files.createDirectories(markerPath.getParent());
    }
    Files.writeString(markerPath, scriptBody + System.lineSeparator());

    Map<String, String> details = new LinkedHashMap<>();
    details.put("markerFile", markerFile);
    details.put("scriptBody", scriptBody);
    return new StepSummary("internalScript", details);
  }
}
