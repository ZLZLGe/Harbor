package com.example.customerprofiles.model;

public class CustomerProfile {

    private final long id;
    private final String companyName;
    private final String segment;
    private final String city;

    public CustomerProfile(long id, String companyName, String segment, String city) {
        this.id = id;
        this.companyName = companyName;
        this.segment = segment;
        this.city = city;
    }

    public long getId() {
        return id;
    }

    public String getCompanyName() {
        return companyName;
    }

    public String getSegment() {
        return segment;
    }

    public String getCity() {
        return city;
    }
}
