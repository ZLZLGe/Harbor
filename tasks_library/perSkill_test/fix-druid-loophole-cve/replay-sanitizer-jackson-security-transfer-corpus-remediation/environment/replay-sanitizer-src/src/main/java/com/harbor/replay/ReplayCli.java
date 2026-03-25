package com.harbor.replay;

import java.nio.file.Path;

public final class ReplayCli
{
  private ReplayCli()
  {
  }

  public static void main(String[] args) throws Exception
  {
    if (args.length != 2) {
      throw new IllegalArgumentException("usage: replay-sanitizer <input-root> <output-file>");
    }

    Path inputRoot = Path.of(args[0]);
    Path outputFile = Path.of(args[1]);
    new ReplaySanitizerService().sanitize(inputRoot, outputFile);
  }
}
