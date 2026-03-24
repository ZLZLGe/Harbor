package com.acme.catalog;

import java.lang.reflect.Method;
import java.util.List;

public final class DescriptorCli {
    public static void main(String[] args) {
        System.out.print(new DescriptorCli().render());
    }

    public String render() {
        try {
            Class<?> generatedClass = Class.forName("com.acme.catalog.generated.OrderFieldsDescriptor");
            Method valuesMethod = generatedClass.getMethod("values");
            @SuppressWarnings("unchecked")
            List<String> values = (List<String>) valuesMethod.invoke(null);
            return String.join(",", values);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("Generated descriptor is unavailable", e);
        }
    }
}
