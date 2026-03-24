package com.example.memberdirectory.dto;

import jakarta.validation.constraints.NotBlank;

public record MemberStatusUpdate(@NotBlank String status) {
}
