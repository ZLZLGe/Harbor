#!/bin/bash
set -euo pipefail

WORKSPACE=${WORKSPACE:-/workspace}
REPO_DIR="${WORKSPACE}/replay-sanitizer"
OUTPUT_FILE="${WORKSPACE}/output/replay-remediation-manifest.json"
SERVICE_FILE="${REPO_DIR}/src/main/java/com/harbor/replay/ReplaySanitizerService.java"

cat > "${SERVICE_FILE}" <<'EOF'
package com.harbor.replay;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.harbor.replay.model.RemediationManifest;
import com.harbor.replay.model.ReplayEnvelope;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

public class ReplaySanitizerService
{
  private static final Set<String> TYPE_DIRECTIVE_KEYS = Set.of("@class", "@type", "@c");
  private static final Set<String> DANGEROUS_TYPES = Set.of("javascript", "groovy", "spel");

  private final ObjectMapper objectMapper;

  public ReplaySanitizerService()
  {
    this.objectMapper = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);
  }

  public void sanitize(Path inputRoot, Path outputFile) throws IOException
  {
    Path batchFile = inputRoot.resolve("batch.json");
    Path requestsDir = inputRoot.resolve("requests");

    RemediationManifest manifest = new RemediationManifest();
    manifest.batchId = objectMapper.readTree(batchFile.toFile()).path("batchId").asText("");

    List<Path> sampleFiles;
    try (Stream<Path> stream = Files.list(requestsDir)) {
      sampleFiles = stream
          .filter(path -> path.getFileName().toString().endsWith(".json"))
          .sorted(Comparator.comparing(path -> path.getFileName().toString()))
          .collect(Collectors.toList());
    }

    for (Path sampleFile : sampleFiles) {
      String rawJson = Files.readString(sampleFile);

      try {
        JsonNode root = objectMapper.readTree(rawJson);
        Set<String> reasons = new LinkedHashSet<>();
        collectReasons(root, reasons);

        ReplayEnvelope envelope = objectMapper.treeToValue(root, ReplayEnvelope.class);
        String sampleId = envelope.sampleId != null
            ? envelope.sampleId
            : sampleFile.getFileName().toString().replace(".json", "");

        if (reasons.isEmpty()) {
          manifest.safeReplays.add(RemediationManifest.SafeReplay.fromEnvelope(envelope));
        } else {
          manifest.quarantinedSamples.add(
              new RemediationManifest.QuarantinedSample(sampleId, sampleFile.getFileName().toString(), new ArrayList<>(reasons))
          );
        }
      }
      catch (JsonProcessingException exception) {
        manifest.quarantinedSamples.add(
            new RemediationManifest.QuarantinedSample(
                sampleFile.getFileName().toString().replace(".json", ""),
                sampleFile.getFileName().toString(),
                List.of("invalid-json")
            )
        );
      }
    }

    manifest.safeReplays.sort(Comparator.comparing(replay -> replay.sampleId));
    manifest.quarantinedSamples.sort(Comparator.comparing(sample -> sample.sampleId));
    manifest.scannedSampleCount = sampleFiles.size();
    manifest.safeReplayCount = manifest.safeReplays.size();
    manifest.quarantinedCount = manifest.quarantinedSamples.size();

    if (outputFile.getParent() != null) {
      Files.createDirectories(outputFile.getParent());
    }
    objectMapper.writeValue(outputFile.toFile(), manifest);
  }

  private void collectReasons(JsonNode node, Set<String> reasons)
  {
    if (node == null) {
      return;
    }

    if (node.isObject()) {
      node.fields().forEachRemaining(entry -> {
        String key = entry.getKey();
        JsonNode value = entry.getValue();

        if (key.isEmpty()) {
          reasons.add("empty-key");
        }
        if (TYPE_DIRECTIVE_KEYS.contains(key)) {
          reasons.add("type-directive");
        }
        if ("type".equals(key) && value.isTextual() && DANGEROUS_TYPES.contains(value.asText().toLowerCase())) {
          reasons.add("script-like-type");
        }

        collectReasons(value, reasons);
      });
      return;
    }

    if (node.isArray()) {
      node.forEach(child -> collectReasons(child, reasons));
    }
  }
}
EOF

cd "${REPO_DIR}"
mvn -q -DskipTests package
java -jar target/replay-sanitizer-1.0-SNAPSHOT.jar "${WORKSPACE}/historical-corpus" "${OUTPUT_FILE}"
