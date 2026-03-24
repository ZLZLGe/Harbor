package com.harbor.reportpreview.model;

public class PreviewOptions
{
  private String locale = "en-US";
  private boolean trimOutput = true;
  private boolean allowExpressions;

  public String getLocale()
  {
    return locale;
  }

  public void setLocale(String locale)
  {
    this.locale = locale;
  }

  public boolean isTrimOutput()
  {
    return trimOutput;
  }

  public void setTrimOutput(boolean trimOutput)
  {
    this.trimOutput = trimOutput;
  }

  public boolean isAllowExpressions()
  {
    return allowExpressions;
  }

  public void setAllowExpressions(boolean allowExpressions)
  {
    this.allowExpressions = allowExpressions;
  }
}
