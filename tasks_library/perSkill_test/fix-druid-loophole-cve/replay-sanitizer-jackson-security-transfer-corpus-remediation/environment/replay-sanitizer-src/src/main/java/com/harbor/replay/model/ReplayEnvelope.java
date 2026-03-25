package com.harbor.replay.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.util.ArrayList;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ReplayEnvelope
{
  public String sampleId;
  public String capturedAt;
  public Request request;

  @JsonIgnoreProperties(ignoreUnknown = true)
  public static class Request
  {
    public String method;
    public String path;
    public Body body;
  }

  @JsonIgnoreProperties(ignoreUnknown = true)
  public static class Body
  {
    public String dataset;
    public Filter filter;
    public Integer limit;
    public List<String> columns = new ArrayList<>();
    public String note;
  }

  @JsonIgnoreProperties(ignoreUnknown = true)
  public static class Filter
  {
    public String type;
    public String dimension;
    public String value;
  }
}
