package com.harbor.pluginmanifest;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.harbor.pluginmanifest.model.ImportReport;
import com.harbor.pluginmanifest.model.ManifestStep;
import com.harbor.pluginmanifest.model.PluginManifest;
import com.harbor.pluginmanifest.model.StepSummary;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public final class ManifestImporter {
  private final ObjectMapper objectMapper;

  public ManifestImporter() {
    this.objectMapper = new ObjectMapper();
  }

  public ImportReport importManifest(Path manifestPath, Path outputPath) throws IOException {
    PluginManifest manifest = objectMapper.readValue(Files.readString(manifestPath), PluginManifest.class);

    List<StepSummary> importedSteps = new ArrayList<>();
    for (ManifestStep step : manifest.getSteps()) {
      importedSteps.add(step.materialize());
    }

    ImportReport report = new ImportReport();
    report.setPluginId(manifest.getPluginId());
    report.setVersion(manifest.getVersion());
    report.setOwner(manifest.getOwner());
    report.setNotes(manifest.getNotes());
    report.setImportedStepCount(importedSteps.size());
    report.setSteps(importedSteps);

    if (outputPath.getParent() != null) {
      Files.createDirectories(outputPath.getParent());
    }
    objectMapper.writerWithDefaultPrettyPrinter().writeValue(outputPath.toFile(), report);
    return report;
  }
}
