package com.harbor.replay.model;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class RemediationManifest
{
  public String batchId;
  public int scannedSampleCount;
  public int safeReplayCount;
  public int quarantinedCount;
  public List<SafeReplay> safeReplays = new ArrayList<>();
  public List<QuarantinedSample> quarantinedSamples = new ArrayList<>();

  public static class SafeReplay
  {
    public String sampleId;
    public String capturedAt;
    public String method;
    public String path;
    public String dataset;
    public String filterType;
    public Map<String, Object> normalizedBody;

    public static SafeReplay fromEnvelope(ReplayEnvelope envelope)
    {
      SafeReplay replay = new SafeReplay();
      replay.sampleId = envelope.sampleId;
      replay.capturedAt = envelope.capturedAt;
      replay.method = envelope.request.method == null ? null : envelope.request.method.toUpperCase();
      replay.path = envelope.request.path;
      replay.dataset = envelope.request.body == null ? null : envelope.request.body.dataset;
      replay.filterType = envelope.request.body == null || envelope.request.body.filter == null
          ? null
          : envelope.request.body.filter.type;

      Map<String, Object> normalized = new LinkedHashMap<>();
      if (envelope.request.body != null) {
        normalized.put("dataset", envelope.request.body.dataset);
        if (envelope.request.body.filter != null) {
          Map<String, Object> filter = new LinkedHashMap<>();
          filter.put("type", envelope.request.body.filter.type);
          filter.put("dimension", envelope.request.body.filter.dimension);
          filter.put("value", envelope.request.body.filter.value);
          normalized.put("filter", filter);
        }
        if (!envelope.request.body.columns.isEmpty()) {
          normalized.put("columns", envelope.request.body.columns);
        }
        if (envelope.request.body.limit != null) {
          normalized.put("limit", envelope.request.body.limit);
        }
        if (envelope.request.body.note != null) {
          normalized.put("note", envelope.request.body.note);
        }
      }
      replay.normalizedBody = normalized;
      return replay;
    }
  }

  public static class QuarantinedSample
  {
    public String sampleId;
    public String sourceFile;
    public List<String> reasons;

    public QuarantinedSample(String sampleId, String sourceFile, List<String> reasons)
    {
      this.sampleId = sampleId;
      this.sourceFile = sourceFile;
      this.reasons = reasons;
    }
  }
}
