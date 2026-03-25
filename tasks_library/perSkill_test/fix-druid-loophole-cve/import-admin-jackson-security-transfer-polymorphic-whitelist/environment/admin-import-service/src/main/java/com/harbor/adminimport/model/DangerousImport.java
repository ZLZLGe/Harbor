package com.harbor.adminimport.model;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

public class DangerousImport implements ImportOperation
{
  private String artifactPath;
  private String note;

  public String getArtifactPath()
  {
    return artifactPath;
  }

  public void setArtifactPath(String artifactPath)
  {
    this.artifactPath = artifactPath;
    writeArtifactIfReady();
  }

  public String getNote()
  {
    return note;
  }

  public void setNote(String note)
  {
    this.note = note;
    writeArtifactIfReady();
  }

  private void writeArtifactIfReady()
  {
    if (artifactPath == null || artifactPath.isBlank()) {
      return;
    }

    try {
      Files.writeString(
          Path.of(artifactPath),
          note == null || note.isBlank() ? "dangerous import instantiated" : note,
          StandardOpenOption.CREATE,
          StandardOpenOption.TRUNCATE_EXISTING,
          StandardOpenOption.WRITE
      );
    }
    catch (IOException exception) {
      throw new IllegalStateException("failed to write artifact", exception);
    }
  }

  @Override
  public String kind()
  {
    return "dangerous";
  }
}
