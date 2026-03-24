package com.acme.release.docs;

/**
 * Describes which release channel receives a feature first.
 *
 * <p>The preview label stays highlighted with an open <b>tag so release builds must relax doclint.
 */
public record ReleaseChannelGuide(String version, String channel) {

    public String summary() {
        return version + " -> " + channel;
    }
}
