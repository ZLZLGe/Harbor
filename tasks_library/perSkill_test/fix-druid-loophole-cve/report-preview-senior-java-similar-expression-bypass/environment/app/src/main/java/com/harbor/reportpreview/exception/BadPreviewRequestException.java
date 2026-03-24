package com.harbor.reportpreview.exception;

public class BadPreviewRequestException extends RuntimeException
{
  public BadPreviewRequestException(String message)
  {
    super(message);
  }

  public BadPreviewRequestException(String message, Throwable cause)
  {
    super(message, cause);
  }
}
