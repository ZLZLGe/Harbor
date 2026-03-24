package com.example.memberdirectory.controller;

import java.util.Map;

import com.example.memberdirectory.dto.RegistrationRequest;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class RegistrationController {

    @PostMapping("/api/members/register")
    public ResponseEntity<Map<String, String>> register(@Valid @RequestBody RegistrationRequest request) {
        return ResponseEntity.ok(Map.of(
            "status", "accepted",
            "email", request.email()
        ));
    }
}
