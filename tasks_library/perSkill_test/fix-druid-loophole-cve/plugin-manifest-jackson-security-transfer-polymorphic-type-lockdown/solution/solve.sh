#!/bin/bash

set -euo pipefail

WORKSPACE=${WORKSPACE:-/root}
APP_DIR=${APP_DIR:-${WORKSPACE}/plugin-manifest-importer}
PATCHES_DIR=${PATCHES_DIR:-${WORKSPACE}/patches}

mkdir -p "${PATCHES_DIR}"

cd "${APP_DIR}"

cat <<'EOF_MANIFEST_IMPORTER' > src/main/java/com/harbor/pluginmanifest/ManifestImporter.java
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
  private final ManifestSecurityInspector manifestSecurityInspector;

  public ManifestImporter() {
    this.objectMapper = new ObjectMapper();
    this.manifestSecurityInspector = new ManifestSecurityInspector();
  }

  public ImportReport importManifest(Path manifestPath, Path outputPath) throws IOException {
    String rawJson = Files.readString(manifestPath);
    manifestSecurityInspector.validate(rawJson);

    PluginManifest manifest = objectMapper.readValue(rawJson, PluginManifest.class);

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
EOF_MANIFEST_IMPORTER

cat <<'EOF_SECURITY_INSPECTOR' > src/main/java/com/harbor/pluginmanifest/ManifestSecurityInspector.java
package com.harbor.pluginmanifest;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;

public final class ManifestSecurityInspector {
  private static final Set<String> FORBIDDEN_TYPE_HINTS = Set.of("@class", "@type");

  private final ObjectMapper objectMapper = new ObjectMapper();

  public void validate(String rawJson) throws IOException {
    inspect(objectMapper.readTree(rawJson), "$");
  }

  private void inspect(JsonNode node, String path) {
    if (node == null) {
      return;
    }

    if (node.isObject()) {
      Iterator<Map.Entry<String, JsonNode>> fields = node.fields();
      while (fields.hasNext()) {
        Map.Entry<String, JsonNode> field = fields.next();
        String fieldName = field.getKey();

        if (FORBIDDEN_TYPE_HINTS.contains(fieldName)) {
          throw new IllegalArgumentException(
              "Manifest contains disallowed polymorphic type hint at " + path + "." + fieldName);
        }

        inspect(field.getValue(), path + "." + fieldName);
      }
      return;
    }

    if (node.isArray()) {
      int index = 0;
      for (JsonNode child : node) {
        inspect(child, path + "[" + index + "]");
        index++;
      }
    }
  }
}
EOF_SECURITY_INSPECTOR

cat <<'EOF_MANIFEST_STEP' > src/main/java/com/harbor/pluginmanifest/model/ManifestStep.java
package com.harbor.pluginmanifest.model;

import com.fasterxml.jackson.annotation.JsonSubTypes;
import com.fasterxml.jackson.annotation.JsonTypeInfo;
import com.harbor.pluginmanifest.steps.CopyAssetStep;
import com.harbor.pluginmanifest.steps.RegisterWebhookStep;
import com.harbor.pluginmanifest.steps.RenderTemplateStep;
import java.io.IOException;

@JsonTypeInfo(use = JsonTypeInfo.Id.NAME, include = JsonTypeInfo.As.PROPERTY, property = "type")
@JsonSubTypes({
    @JsonSubTypes.Type(value = CopyAssetStep.class, name = "copyAsset"),
    @JsonSubTypes.Type(value = RenderTemplateStep.class, name = "renderTemplate"),
    @JsonSubTypes.Type(value = RegisterWebhookStep.class, name = "registerWebhook")
})
public interface ManifestStep {
  StepSummary materialize() throws IOException;
}
EOF_MANIFEST_STEP

git diff -- src/main/java/com/harbor/pluginmanifest/ManifestImporter.java \
  src/main/java/com/harbor/pluginmanifest/model/ManifestStep.java \
  > "${PATCHES_DIR}/0001-lock-down-plugin-manifest-polymorphic-steps.patch"

git diff --no-index -- /dev/null src/main/java/com/harbor/pluginmanifest/ManifestSecurityInspector.java \
  >> "${PATCHES_DIR}/0001-lock-down-plugin-manifest-polymorphic-steps.patch" || true

mvn package -DskipTests
