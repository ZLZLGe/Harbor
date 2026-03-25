package com.example.annotation;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;
import org.junit.jupiter.api.Test;

class PrefixProcessorTest {
    @Test
    void returnsUpperCasePrefixes() {
        PrefixProcessor processor = new PrefixProcessor();
        assertEquals(List.of("A", "B", "G"), processor.previewPrefixes(List.of("alpha", "beta", "gamma")));
    }
}
