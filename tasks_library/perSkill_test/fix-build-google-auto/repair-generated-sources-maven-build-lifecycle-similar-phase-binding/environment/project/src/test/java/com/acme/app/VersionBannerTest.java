package com.acme.app;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class VersionBannerTest {
    @Test
    void rendersGeneratedMetadata() {
        assertEquals("LedgerSync@canary#2026.03.25", VersionBanner.render());
    }
}
