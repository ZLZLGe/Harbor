package com.harbor.replay;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.harbor.replay.model.RemediationManifest;
import com.harbor.replay.model.ReplayEnvelope;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.Stream;

public class ReplaySanitizerService
{
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
      try {
        ReplayEnvelope envelope = objectMapper.readValue(sampleFile.toFile(), ReplayEnvelope.class);
        List<String> reasons = findReasons(envelope);
        if (reasons.isEmpty()) {
          manifest.safeReplays.add(RemediationManifest.SafeReplay.fromEnvelope(envelope));
        } else {
          manifest.quarantinedSamples.add(
              new RemediationManifest.QuarantinedSample(
                  envelope.sampleId,
                  sampleFile.getFileName().toString(),
                  reasons
              )
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

    manifest.scannedSampleCount = sampleFiles.size();
    manifest.safeReplayCount = manifest.safeReplays.size();
    manifest.quarantinedCount = manifest.quarantinedSamples.size();

    if (outputFile.getParent() != null) {
      Files.createDirectories(outputFile.getParent());
    }
    objectMapper.writeValue(outputFile.toFile(), manifest);
  }

  private List<String> findReasons(ReplayEnvelope envelope)
  {
    if (envelope.request == null || envelope.request.body == null || envelope.request.body.filter == null) {
      return List.of();
    }

    String filterType = envelope.request.body.filter.type;
    if (filterType == null) {
      return List.of();
    }

    if ("javascript".equalsIgnoreCase(filterType)
        || "groovy".equalsIgnoreCase(filterType)
        || "spel".equalsIgnoreCase(filterType)) {
      return List.of("script-like-type");
    }

    return List.of();
  }
}
