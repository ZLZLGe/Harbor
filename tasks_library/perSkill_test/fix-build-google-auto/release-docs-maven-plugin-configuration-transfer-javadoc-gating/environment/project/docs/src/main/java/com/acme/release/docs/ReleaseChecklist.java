package com.acme.release.docs;

/**
 * Provides a stable heading used by release documentation tooling.
 */
public final class ReleaseChecklist {

    private ReleaseChecklist() {
    }

    public static String heading() {
        return "release:preview";
    }
}
