package com.acme.app;

import com.acme.build.BuildMetadata;

public final class VersionBanner {
    private VersionBanner() {
    }

    public static String render() {
        return BuildMetadata.describe();
    }
}
