package com.example.memberdirectory.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

public record RegistrationRequest(
    @NotBlank String displayName,
    @Email String email
) {
}
