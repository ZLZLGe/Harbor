package com.harbor.adminimport.model;

import java.util.List;

public class ImportEnvelope
{
  private String batchId;
  private List<ImportOperation> operations;

  public String getBatchId()
  {
    return batchId;
  }

  public void setBatchId(String batchId)
  {
    this.batchId = batchId;
  }

  public List<ImportOperation> getOperations()
  {
    return operations;
  }

  public void setOperations(List<ImportOperation> operations)
  {
    this.operations = operations;
  }
}
