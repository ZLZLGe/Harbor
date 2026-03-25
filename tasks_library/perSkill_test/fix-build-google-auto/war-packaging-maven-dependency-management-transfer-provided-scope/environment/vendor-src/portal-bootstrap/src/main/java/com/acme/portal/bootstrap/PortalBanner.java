package com.acme.portal.bootstrap;

import org.apache.commons.lang3.StringUtils;

public final class PortalBanner {
    private PortalBanner() {
    }

    public static String render(String portalName) {
        return "Welcome, " + StringUtils.capitalize(portalName);
    }
}
