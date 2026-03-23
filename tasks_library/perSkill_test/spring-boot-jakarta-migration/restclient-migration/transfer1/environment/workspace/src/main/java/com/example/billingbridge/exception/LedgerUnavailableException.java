package com.example.billingbridge.exception;

public class LedgerUnavailableException extends RuntimeException {

    public LedgerUnavailableException(String message) {
        super(message);
    }
}
