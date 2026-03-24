package com.harbor.pluginmanifest.model;

import com.fasterxml.jackson.annotation.JsonTypeInfo;
import java.io.IOException;

@JsonTypeInfo(use = JsonTypeInfo.Id.CLASS, include = JsonTypeInfo.As.PROPERTY, property = "@class")
public interface ManifestStep {
  StepSummary materialize() throws IOException;
}
