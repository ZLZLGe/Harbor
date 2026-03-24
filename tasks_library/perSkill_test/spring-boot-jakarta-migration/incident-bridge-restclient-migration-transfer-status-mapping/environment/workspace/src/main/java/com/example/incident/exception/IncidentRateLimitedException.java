package com.example.incident.exception;

public class IncidentRateLimitedException extends RuntimeException {

    private final long retryAfterSeconds;

    public IncidentRateLimitedException(String message, long retryAfterSeconds) {
        super(message);
        this.retryAfterSeconds = retryAfterSeconds;
    }

    public long getRetryAfterSeconds() {
        return retryAfterSeconds;
    }
}
