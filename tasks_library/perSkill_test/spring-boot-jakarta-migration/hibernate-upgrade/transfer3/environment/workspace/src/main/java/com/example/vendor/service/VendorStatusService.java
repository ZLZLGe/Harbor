package com.example.vendor.service;

import javax.transaction.Transactional;
import org.springframework.stereotype.Service;

@Service
public class VendorStatusService {
    @Transactional
    public String initialStatus() {
        return "pending-review";
    }
}
