package com.example.vendor.controller;

import com.example.vendor.dto.OnboardVendorRequest;
import java.util.Map;
import javax.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/vendors")
public class VendorController {
    @PostMapping
    public Map<String, String> onboard(@Valid @RequestBody OnboardVendorRequest request) {
        return Map.of("vendorCode", request.getVendorCode(), "displayName", request.getDisplayName());
    }
}
