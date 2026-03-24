package com.harbor.preview;

import java.util.List;
import java.util.Map;

public class PreviewResponse
{
  private final boolean scriptApplied;
  private final String expression;
  private final List<Map<String, Object>> rows;
  private final int rowCount;

  public PreviewResponse(boolean scriptApplied, String expression, List<Map<String, Object>> rows)
  {
    this.scriptApplied = scriptApplied;
    this.expression = expression;
    this.rows = rows;
    this.rowCount = rows.size();
  }

  public boolean isScriptApplied()
  {
    return scriptApplied;
  }

  public String getExpression()
  {
    return expression;
  }

  public List<Map<String, Object>> getRows()
  {
    return rows;
  }

  public int getRowCount()
  {
    return rowCount;
  }
}
