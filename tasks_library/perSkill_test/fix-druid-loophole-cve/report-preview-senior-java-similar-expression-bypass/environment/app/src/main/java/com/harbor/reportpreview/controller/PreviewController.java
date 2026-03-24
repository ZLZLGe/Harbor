package com.harbor.reportpreview.controller;

import com.harbor.reportpreview.model.PreviewRequest;
import com.harbor.reportpreview.model.PreviewResponse;
import com.harbor.reportpreview.service.PreviewRequestParser;
import com.harbor.reportpreview.service.ReportPreviewService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/reports")
public class PreviewController
{
  private final PreviewRequestParser previewRequestParser;
  private final ReportPreviewService reportPreviewService;

  public PreviewController(
      PreviewRequestParser previewRequestParser,
      ReportPreviewService reportPreviewService
  )
  {
    this.previewRequestParser = previewRequestParser;
    this.reportPreviewService = reportPreviewService;
  }

  @GetMapping("/health")
  public String health()
  {
    return "ok";
  }

  @PostMapping(value = "/preview", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
  public PreviewResponse preview(@RequestBody String rawJson)
  {
    PreviewRequest request = previewRequestParser.parse(rawJson);
    return reportPreviewService.preview(request);
  }
}
