package com.harbor.adminimport.model;

import java.util.List;

public class DashboardImport implements ImportOperation
{
  private String dashboardName;
  private List<String> widgets;

  public String getDashboardName()
  {
    return dashboardName;
  }

  public void setDashboardName(String dashboardName)
  {
    this.dashboardName = dashboardName;
  }

  public List<String> getWidgets()
  {
    return widgets;
  }

  public void setWidgets(List<String> widgets)
  {
    this.widgets = widgets;
  }

  @Override
  public String kind()
  {
    return "dashboard";
  }
}
