package com.harbor.reportpreview.model;

import java.util.Map;

public class PreviewRequest
{
  private final String template;
  private final Map<String, String> variables;
  private final PreviewOptions options;

  public PreviewRequest(String template, Map<String, String> variables, PreviewOptions options)
  {
    this.template = template;
    this.variables = variables;
    this.options = options;
  }

  public String getTemplate()
  {
    return template;
  }

  public Map<String, String> getVariables()
  {
    return variables;
  }

  public PreviewOptions getOptions()
  {
    return options;
  }
}
