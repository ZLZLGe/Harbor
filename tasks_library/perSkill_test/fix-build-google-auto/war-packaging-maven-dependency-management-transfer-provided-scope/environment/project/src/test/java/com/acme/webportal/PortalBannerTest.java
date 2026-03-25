package com.acme.webportal;

import com.acme.portal.bootstrap.PortalBanner;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class PortalBannerTest {
    @Test
    void rendersCapitalizedBanner() {
        assertEquals("Welcome, Harbor", PortalBanner.render("harbor"));
    }
}
