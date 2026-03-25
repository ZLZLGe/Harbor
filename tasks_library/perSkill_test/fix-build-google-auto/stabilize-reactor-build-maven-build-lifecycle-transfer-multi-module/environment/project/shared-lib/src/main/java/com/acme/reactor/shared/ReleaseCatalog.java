package com.acme.reactor.shared;

import java.util.List;

public final class ReleaseCatalog {
    private ReleaseCatalog() {
    }

    public static String releaseName() {
        return "nightly-ops";
    }

    public static List<String> orderedStages() {
        return List.of("prepare-assets", "warm-services", "announce-window");
    }
}
