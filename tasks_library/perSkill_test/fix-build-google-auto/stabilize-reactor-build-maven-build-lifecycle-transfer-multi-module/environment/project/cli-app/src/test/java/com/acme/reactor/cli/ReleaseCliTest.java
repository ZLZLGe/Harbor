package com.acme.reactor.cli;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class ReleaseCliTest {
    @Test
    void buildsExpectedPlanLine() {
        assertEquals(
                "PLAN: nightly-ops|prepare-assets>warm-services>announce-window",
                ReleaseCli.buildLine()
        );
    }
}
