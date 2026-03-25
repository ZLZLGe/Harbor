package com.example.approval.web;

import com.example.approval.model.LoginRequest;
import java.util.Map;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/session")
public class SessionController {

    @PostMapping("/login")
    public Map<String, String> login(@RequestBody LoginRequest request) {
        return Map.of(
            "user", request.username(),
            "sessionToken", "session-" + request.username()
        );
    }
}
