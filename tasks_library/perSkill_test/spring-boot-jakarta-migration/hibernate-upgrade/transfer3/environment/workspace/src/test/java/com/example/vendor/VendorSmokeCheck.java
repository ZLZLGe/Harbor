package com.example.vendor;

import com.example.vendor.bootstrap.VendorBootstrap;
import com.example.vendor.controller.VendorController;
import com.example.vendor.dto.OnboardVendorRequest;
import com.example.vendor.service.VendorStatusService;
import java.util.Map;

public class VendorSmokeCheck {
    public static void main(String[] args) {
        new VendorBootstrap().init();
        if (!"true".equals(System.getProperty("vendor.bootstrap.ready"))) {
            throw new AssertionError("bootstrap did not run");
        }

        if (!"pending-review".equals(new VendorStatusService().initialStatus())) {
            throw new AssertionError("service status mismatch");
        }

        OnboardVendorRequest request = new OnboardVendorRequest();
        request.setVendorCode("V-88");
        request.setContactEmail("ops@example.com");
        request.setDisplayName("Northwind");
        Map<String, String> result = new VendorController().onboard(request);
        if (!"Northwind".equals(result.get("displayName"))) {
            throw new AssertionError("controller output mismatch");
        }
    }
}
