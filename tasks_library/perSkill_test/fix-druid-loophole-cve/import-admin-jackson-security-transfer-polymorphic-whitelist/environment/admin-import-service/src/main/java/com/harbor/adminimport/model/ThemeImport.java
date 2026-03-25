package com.harbor.adminimport.model;

import java.util.List;

public class ThemeImport implements ImportOperation
{
  private String themeName;
  private List<String> palette;

  public String getThemeName()
  {
    return themeName;
  }

  public void setThemeName(String themeName)
  {
    this.themeName = themeName;
  }

  public List<String> getPalette()
  {
    return palette;
  }

  public void setPalette(List<String> palette)
  {
    this.palette = palette;
  }

  @Override
  public String kind()
  {
    return "theme";
  }
}
