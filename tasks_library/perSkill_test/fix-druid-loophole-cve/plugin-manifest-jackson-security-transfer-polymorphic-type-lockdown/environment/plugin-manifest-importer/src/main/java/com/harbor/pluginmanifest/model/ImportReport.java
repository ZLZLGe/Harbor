package com.harbor.pluginmanifest.model;

import java.util.ArrayList;
import java.util.List;

public final class ImportReport {
  private String pluginId;
  private String version;
  private String owner;
  private String notes;
  private int importedStepCount;
  private List<StepSummary> steps = new ArrayList<>();

  public String getPluginId() {
    return pluginId;
  }

  public void setPluginId(String pluginId) {
    this.pluginId = pluginId;
  }

  public String getVersion() {
    return version;
  }

  public void setVersion(String version) {
    this.version = version;
  }

  public String getOwner() {
    return owner;
  }

  public void setOwner(String owner) {
    this.owner = owner;
  }

  public String getNotes() {
    return notes;
  }

  public void setNotes(String notes) {
    this.notes = notes;
  }

  public int getImportedStepCount() {
    return importedStepCount;
  }

  public void setImportedStepCount(int importedStepCount) {
    this.importedStepCount = importedStepCount;
  }

  public List<StepSummary> getSteps() {
    return steps;
  }

  public void setSteps(List<StepSummary> steps) {
    this.steps = steps;
  }
}
