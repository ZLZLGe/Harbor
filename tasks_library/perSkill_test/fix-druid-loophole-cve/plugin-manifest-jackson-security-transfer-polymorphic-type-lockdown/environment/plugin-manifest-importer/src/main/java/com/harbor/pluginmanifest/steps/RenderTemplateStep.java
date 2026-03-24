package com.harbor.pluginmanifest.steps;

import com.harbor.pluginmanifest.model.ManifestStep;
import com.harbor.pluginmanifest.model.StepSummary;
import java.util.LinkedHashMap;
import java.util.Map;

public final class RenderTemplateStep implements ManifestStep {
  private String template;
  private String outputPath;

  public String getTemplate() {
    return template;
  }

  public void setTemplate(String template) {
    this.template = template;
  }

  public String getOutputPath() {
    return outputPath;
  }

  public void setOutputPath(String outputPath) {
    this.outputPath = outputPath;
  }

  @Override
  public StepSummary materialize() {
    Map<String, String> details = new LinkedHashMap<>();
    details.put("template", template);
    details.put("outputPath", outputPath);
    return new StepSummary("renderTemplate", details);
  }
}
