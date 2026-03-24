package com.harbor.reportpreview.model;

public class PreviewResponse
{
  private final String rendered;
  private final String engine;

  public PreviewResponse(String rendered, String engine)
  {
    this.rendered = rendered;
    this.engine = engine;
  }

  public String getRendered()
  {
    return rendered;
  }

  public String getEngine()
  {
    return engine;
  }
}
