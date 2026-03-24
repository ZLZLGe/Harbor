package com.acme.build;

import java.io.IOException;
import java.io.Writer;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import javax.annotation.processing.AbstractProcessor;
import javax.annotation.processing.ProcessingEnvironment;
import javax.annotation.processing.RoundEnvironment;
import javax.annotation.processing.SupportedOptions;
import javax.lang.model.SourceVersion;
import javax.lang.model.element.AnnotationMirror;
import javax.lang.model.element.AnnotationValue;
import javax.lang.model.element.Element;
import javax.lang.model.element.TypeElement;
import javax.tools.JavaFileObject;

@SupportedOptions({"descriptor.package", "descriptor.className"})
public final class DescriptorProcessor extends AbstractProcessor {
    private static final String TARGET_ANNOTATION = "com.acme.catalog.DescriptorSpec";
    private boolean generated;

    @Override
    public synchronized void init(ProcessingEnvironment processingEnv) {
        super.init(processingEnv);
        this.generated = false;
    }

    @Override
    public Set<String> getSupportedAnnotationTypes() {
        return Set.of(TARGET_ANNOTATION);
    }

    @Override
    public SourceVersion getSupportedSourceVersion() {
        return SourceVersion.latestSupported();
    }

    @Override
    public boolean process(Set<? extends TypeElement> annotations, RoundEnvironment roundEnv) {
        if (generated || roundEnv.processingOver()) {
            return false;
        }

        for (Element element : roundEnv.getRootElements()) {
            for (AnnotationMirror mirror : element.getAnnotationMirrors()) {
                if (!TARGET_ANNOTATION.equals(mirror.getAnnotationType().toString())) {
                    continue;
                }

                List<String> values = readValues(mirror);
                writeDescriptor(values);
                generated = true;
                return true;
            }
        }

        return false;
    }

    private List<String> readValues(AnnotationMirror mirror) {
        List<String> values = new ArrayList<>();
        for (Map.Entry<? extends javax.lang.model.element.ExecutableElement, ? extends AnnotationValue> entry
                : mirror.getElementValues().entrySet()) {
            if (!"value".equals(entry.getKey().getSimpleName().toString())) {
                continue;
            }
            @SuppressWarnings("unchecked")
            List<? extends AnnotationValue> rawValues = (List<? extends AnnotationValue>) entry.getValue().getValue();
            for (AnnotationValue rawValue : rawValues) {
                values.add(String.valueOf(rawValue.getValue()));
            }
        }
        return values;
    }

    private void writeDescriptor(List<String> values) {
        String packageName = processingEnv.getOptions().getOrDefault("descriptor.package", "com.acme.catalog.generated");
        String className = processingEnv.getOptions().getOrDefault("descriptor.className", "GeneratedDescriptor");
        String qualifiedName = packageName + "." + className;

        try {
            JavaFileObject file = processingEnv.getFiler().createSourceFile(qualifiedName);
            try (Writer writer = file.openWriter()) {
                writer.write("package " + packageName + ";\n\n");
                writer.write("import java.util.List;\n\n");
                writer.write("public final class " + className + " {\n");
                writer.write("    private " + className + "() {\n");
                writer.write("    }\n\n");
                writer.write("    public static List<String> values() {\n");
                writer.write("        return List.of(");
                for (int i = 0; i < values.size(); i++) {
                    if (i > 0) {
                        writer.write(", ");
                    }
                    writer.write("\"" + values.get(i) + "\"");
                }
                writer.write(");\n");
                writer.write("    }\n");
                writer.write("}\n");
            }
        } catch (IOException e) {
            throw new IllegalStateException("Failed to generate descriptor source", e);
        }
    }
}
