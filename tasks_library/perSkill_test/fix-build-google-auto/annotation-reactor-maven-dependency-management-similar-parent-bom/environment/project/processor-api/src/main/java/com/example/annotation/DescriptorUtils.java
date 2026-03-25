package com.example.annotation;

import com.google.common.collect.Streams;
import java.util.List;
import java.util.stream.Collectors;

public final class DescriptorUtils {
    private DescriptorUtils() {
    }

    public static List<String> prefixes(Iterable<String> values) {
        return Streams.stream(values)
                .map(value -> value.substring(0, 1).toUpperCase())
                .collect(Collectors.toList());
    }
}
