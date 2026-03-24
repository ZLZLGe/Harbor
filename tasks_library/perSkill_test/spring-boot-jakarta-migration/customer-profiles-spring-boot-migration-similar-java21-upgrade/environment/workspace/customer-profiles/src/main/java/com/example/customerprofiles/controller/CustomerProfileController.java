package com.example.customerprofiles.controller;

import com.example.customerprofiles.model.CustomerProfile;
import com.example.customerprofiles.service.CustomerProfileService;
import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/profiles")
public class CustomerProfileController {

    private final CustomerProfileService customerProfileService;

    public CustomerProfileController(CustomerProfileService customerProfileService) {
        this.customerProfileService = customerProfileService;
    }

    @GetMapping
    public List<CustomerProfile> getProfiles() {
        return customerProfileService.findAll();
    }

    @GetMapping("/{id}")
    public ResponseEntity<CustomerProfile> getProfile(@PathVariable long id) {
        return customerProfileService.findById(id)
            .map(ResponseEntity::ok)
            .orElseGet(() -> ResponseEntity.notFound().build());
    }
}
