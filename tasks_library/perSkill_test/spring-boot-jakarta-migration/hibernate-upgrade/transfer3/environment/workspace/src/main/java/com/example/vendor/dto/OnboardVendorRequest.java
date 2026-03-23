package com.example.vendor.dto;

import javax.validation.constraints.*;

public class OnboardVendorRequest {
    @NotBlank
    private String vendorCode;

    @Email
    private String contactEmail;

    @Size(min = 2, max = 80)
    private String displayName;

    public String getVendorCode() {
        return vendorCode;
    }

    public void setVendorCode(String vendorCode) {
        this.vendorCode = vendorCode;
    }

    public String getContactEmail() {
        return contactEmail;
    }

    public void setContactEmail(String contactEmail) {
        this.contactEmail = contactEmail;
    }

    public String getDisplayName() {
        return displayName;
    }

    public void setDisplayName(String displayName) {
        this.displayName = displayName;
    }
}
