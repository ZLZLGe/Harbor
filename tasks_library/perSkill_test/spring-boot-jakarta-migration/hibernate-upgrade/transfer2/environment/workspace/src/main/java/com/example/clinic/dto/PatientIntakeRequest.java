package com.example.clinic.dto;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Size;

public class PatientIntakeRequest {
    @NotBlank
    private String patientCode;

    @Size(min = 3, max = 120)
    private String symptomSummary;

    public String getPatientCode() {
        return patientCode;
    }

    public void setPatientCode(String patientCode) {
        this.patientCode = patientCode;
    }

    public String getSymptomSummary() {
        return symptomSummary;
    }

    public void setSymptomSummary(String symptomSummary) {
        this.symptomSummary = symptomSummary;
    }
}
