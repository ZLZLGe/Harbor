package com.example.incidents.repository;

import com.example.incidents.model.IncidentCase;
import java.util.List;

public interface IncidentCaseSearchRepository {
    List<IncidentCase> findOpenCasesByTeam(String ownerTeam);
}
