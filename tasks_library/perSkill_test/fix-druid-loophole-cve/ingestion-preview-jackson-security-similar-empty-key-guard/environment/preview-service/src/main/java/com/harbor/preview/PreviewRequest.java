package com.harbor.preview;

import com.fasterxml.jackson.annotation.JsonAnySetter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class PreviewRequest
{
  private SourceConfig source = new SourceConfig();
  private TransformConfig transform = new TransformConfig();

  public SourceConfig getSource()
  {
    return source;
  }

  public void setSource(SourceConfig source)
  {
    this.source = source;
  }

  public TransformConfig getTransform()
  {
    return transform;
  }

  public void setTransform(TransformConfig transform)
  {
    this.transform = transform;
  }

  public static class SourceConfig
  {
    private List<Map<String, Object>> rows = new ArrayList<>();

    public List<Map<String, Object>> getRows()
    {
      return rows;
    }

    public void setRows(List<Map<String, Object>> rows)
    {
      this.rows = rows;
    }
  }

  public static class TransformConfig
  {
    private String mode = "select";
    private String field;
    private String expression;
    private ScriptPolicy scriptPolicy = new ScriptPolicy(false);

    public String getMode()
    {
      return mode;
    }

    public void setMode(String mode)
    {
      this.mode = mode;
    }

    public String getField()
    {
      return field;
    }

    public void setField(String field)
    {
      this.field = field;
    }

    public String getExpression()
    {
      return expression;
    }

    public void setExpression(String expression)
    {
      this.expression = expression;
    }

    public ScriptPolicy getScriptPolicy()
    {
      return scriptPolicy;
    }

    public void setScriptPolicy(ScriptPolicy scriptPolicy)
    {
      this.scriptPolicy = scriptPolicy;
    }

    public boolean isScriptMode()
    {
      return "script".equalsIgnoreCase(mode);
    }

    public boolean isScriptEnabled()
    {
      return scriptPolicy != null && scriptPolicy.isEnabled();
    }

    @JsonAnySetter
    public void captureUnknownField(String key, Object value)
    {
      if ("".equals(key) && value instanceof Map<?, ?> rawMap) {
        Object enabled = rawMap.get("enabled");
        if (enabled instanceof Boolean enabledFlag) {
          this.scriptPolicy = new ScriptPolicy(enabledFlag);
        }
      }
    }
  }

  public static class ScriptPolicy
  {
    private boolean enabled;

    public ScriptPolicy()
    {
    }

    public ScriptPolicy(boolean enabled)
    {
      this.enabled = enabled;
    }

    public boolean isEnabled()
    {
      return enabled;
    }

    public void setEnabled(boolean enabled)
    {
      this.enabled = enabled;
    }
  }
}
