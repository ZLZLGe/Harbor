package com.harbor.reportpreview.service;

import com.harbor.reportpreview.model.PreviewRequest;
import com.harbor.reportpreview.model.PreviewResponse;
import java.util.Map;
import org.springframework.expression.ExpressionParser;
import org.springframework.expression.common.TemplateParserContext;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.expression.spel.support.StandardEvaluationContext;
import org.springframework.stereotype.Service;

@Service
public class ReportPreviewService
{
  private final ExpressionParser expressionParser = new SpelExpressionParser();

  public PreviewResponse preview(PreviewRequest request)
  {
    String rendered = request.getOptions().isAllowExpressions()
        ? renderAsExpression(request)
        : renderAsTemplate(request);

    if (request.getOptions().isTrimOutput()) {
      rendered = rendered.trim();
    }

    String engine = request.getOptions().isAllowExpressions() ? "expression" : "template";
    return new PreviewResponse(rendered, engine);
  }

  private String renderAsTemplate(PreviewRequest request)
  {
    String rendered = request.getTemplate();
    for (Map.Entry<String, String> entry : request.getVariables().entrySet()) {
      rendered = rendered.replace("{{" + entry.getKey() + "}}", entry.getValue());
    }
    return rendered;
  }

  private String renderAsExpression(PreviewRequest request)
  {
    StandardEvaluationContext context = new StandardEvaluationContext();
    request.getVariables().forEach(context::setVariable);
    return expressionParser
        .parseExpression(request.getTemplate(), new TemplateParserContext())
        .getValue(context, String.class);
  }
}
