package com.example.customerprofile.dto;

public record WelcomeMessageRequest(
        String customerId,
        String templateCode) {
}
