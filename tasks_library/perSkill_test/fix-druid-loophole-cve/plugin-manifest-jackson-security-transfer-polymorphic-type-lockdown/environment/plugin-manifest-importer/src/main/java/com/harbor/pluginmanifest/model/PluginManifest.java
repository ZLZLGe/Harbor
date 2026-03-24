package com.harbor.pluginmanifest.model;

import java.util.ArrayList;
import java.util.List;

public final class PluginManifest {
  private String pluginId;
  private String version;
  private String owner;
  private String notes;
  private List<ManifestStep> steps = new ArrayList<>();

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

  public List<ManifestStep> getSteps() {
    return steps;
  }

  public void setSteps(List<ManifestStep> steps) {
    this.steps = steps;
  }
}
