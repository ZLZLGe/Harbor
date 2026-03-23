package com.example.clinic.controller;

import com.example.clinic.dto.PatientIntakeRequest;
import java.util.Map;
import javax.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/intake")
public class PatientIntakeController {
    @PostMapping
    public Map<String, String> submit(@Valid @RequestBody PatientIntakeRequest request) {
        return Map.of("patientCode", request.getPatientCode());
    }
}
