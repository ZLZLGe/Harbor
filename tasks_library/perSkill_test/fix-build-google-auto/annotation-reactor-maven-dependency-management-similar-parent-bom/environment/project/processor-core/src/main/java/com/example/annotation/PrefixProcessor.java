package com.example.annotation;

import com.google.auto.service.AutoService;
import java.util.List;
import javax.annotation.processing.AbstractProcessor;
import javax.annotation.processing.Processor;
import javax.lang.model.SourceVersion;
import javax.lang.model.element.TypeElement;

@AutoService(Processor.class)
public final class PrefixProcessor extends AbstractProcessor {
    public List<String> previewPrefixes(Iterable<String> values) {
        return DescriptorUtils.prefixes(values);
    }

    @Override
    public boolean process(java.util.Set<? extends TypeElement> annotations,
            javax.annotation.processing.RoundEnvironment roundEnv) {
        return false;
    }

    @Override
    public java.util.Set<String> getSupportedAnnotationTypes() {
        return java.util.Collections.singleton("*");
    }

    @Override
    public SourceVersion getSupportedSourceVersion() {
        return SourceVersion.latestSupported();
    }
}
