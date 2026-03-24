package com.example.customerprofiles.service;

import com.example.customerprofiles.model.CustomerProfile;
import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Service;

@Service
public class CustomerProfileService {

    private final List<CustomerProfile> profiles = List.of(
        new CustomerProfile(1L, "Harbor Retail", "enterprise", "Hong Kong"),
        new CustomerProfile(2L, "Northwind Labs", "mid-market", "Singapore"),
        new CustomerProfile(3L, "Blue Atlas Foods", "small-business", "Sydney")
    );

    public List<CustomerProfile> findAll() {
        return profiles;
    }

    public Optional<CustomerProfile> findById(long id) {
        return profiles.stream().filter(profile -> profile.getId() == id).findFirst();
    }
}
