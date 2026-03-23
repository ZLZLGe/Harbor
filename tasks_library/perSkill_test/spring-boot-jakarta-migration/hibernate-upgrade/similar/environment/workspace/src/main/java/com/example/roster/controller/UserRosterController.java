package com.example.roster.controller;

import com.example.roster.dto.UserSignupRequest;
import java.util.Map;
import javax.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/roster")
public class UserRosterController {
    @PostMapping("/signup")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public Map<String, String> signup(@Valid @RequestBody UserSignupRequest request) {
        return Map.of("employeeId", request.getEmployeeId(), "email", request.getEmail());
    }
}
