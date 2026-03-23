package com.example.customerprofile.dto;

public record CustomerProfile(
        String customerId,
        String fullName,
        String tier,
        boolean active) {
}
