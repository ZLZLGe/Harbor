package com.example.incidents.model;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.Id;
import javax.persistence.Table;

@Entity
@Table(name = "incident_cases")
public class IncidentCase {
    @Id
    private Long id;

    @Column(nullable = false)
    private String ownerTeam;

    @Column(nullable = false)
    private boolean open;

    @Column(nullable = false)
    private int severity;
}
