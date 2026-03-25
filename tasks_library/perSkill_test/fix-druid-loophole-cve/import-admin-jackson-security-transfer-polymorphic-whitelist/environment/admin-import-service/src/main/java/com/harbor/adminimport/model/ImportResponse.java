package com.harbor.adminimport.model;

import java.util.List;

public class ImportResponse
{
  private final String batchId;
  private final int importedCount;
  private final List<String> importedKinds;

  public ImportResponse(String batchId, int importedCount, List<String> importedKinds)
  {
    this.batchId = batchId;
    this.importedCount = importedCount;
    this.importedKinds = importedKinds;
  }

  public String getBatchId()
  {
    return batchId;
  }

  public int getImportedCount()
  {
    return importedCount;
  }

  public List<String> getImportedKinds()
  {
    return importedKinds;
  }
}
