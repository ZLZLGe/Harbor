package com.example.roster.dto;

import javax.validation.constraints.Email;
import javax.validation.constraints.NotBlank;

public class UserSignupRequest {
    @NotBlank
    private String employeeId;

    @Email
    private String email;

    public String getEmployeeId() {
        return employeeId;
    }

    public void setEmployeeId(String employeeId) {
        this.employeeId = employeeId;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }
}
