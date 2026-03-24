Complete the workbook at `/root/data/readmission_risk_dashboard.xlsx`.

The workbook already contains:
- `Admissions`: raw inpatient intake observations
- `RiskScoring`: an empty worksheet for patient-level outputs
- `WardSummary`: an empty worksheet for ward-level triage outputs

Column notes are summarized in `/root/data/readmission-readme.md`.

Do not alter `Admissions`. Write plain values to the output sheets; formulas are not required.

Populate `RiskScoring` with one row per admission, keeping the same row order as `Admissions`.
Create these columns in this exact order:
1. `AdmissionID`
2. `Ward`
3. `Age`
4. `AgeBand`
5. `AgePoints`
6. `PriorAdmissions90D`
7. `PriorAdmissionPoints`
8. `HeartRate`
9. `SystolicBP`
10. `RespiratoryRate`
11. `OxygenSaturation`
12. `TemperatureC`
13. `TachycardiaFlag`
14. `HypotensionFlag`
15. `TachypneaFlag`
16. `HypoxiaFlag`
17. `FeverFlag`
18. `CharlsonIndex`
19. `HighCharlsonFlag`
20. `ComorbidityCount`
21. `ReadmissionRiskScore`
22. `RiskTier`

Feature rules:
- `AgeBand`:
  - `<50` if `Age < 50`
  - `50-64` if `50 <= Age <= 64`
  - `65-79` if `65 <= Age <= 79`
  - `80+` if `Age >= 80`
- `AgePoints`:
  - `0` for `<50`
  - `1` for `50-64`
  - `2` for `65-79`
  - `3` for `80+`
- `PriorAdmissionPoints`:
  - `0` if `PriorAdmissions90D = 0`
  - `2` if `PriorAdmissions90D = 1`
  - `4` if `PriorAdmissions90D >= 2`
- `TachycardiaFlag = 1` if `HeartRate >= 110`, else `0`
- `HypotensionFlag = 1` if `SystolicBP < 100`, else `0`
- `TachypneaFlag = 1` if `RespiratoryRate >= 24`, else `0`
- `HypoxiaFlag = 1` if `OxygenSaturation < 94`, else `0`
- `FeverFlag = 1` if `TemperatureC >= 38.0`, else `0`
- `HighCharlsonFlag = 1` if `CharlsonIndex >= 5`, else `0`
- `ComorbidityCount = HasCOPD + HasCHF + HasDiabetes + HasCKD`

Risk score rule:
- `ReadmissionRiskScore = AgePoints + PriorAdmissionPoints + 2*TachycardiaFlag + 2*HypotensionFlag + TachypneaFlag + 2*HypoxiaFlag + FeverFlag + 2*HighCharlsonFlag + ComorbidityCount`

Risk tier rule:
- `Low` if `ReadmissionRiskScore <= 4`
- `Medium` if `ReadmissionRiskScore >= 5` and `<= 9`
- `High` if `ReadmissionRiskScore >= 10`

Populate `WardSummary` with one row per ward, sorted alphabetically by `Ward`.
Create these columns in this exact order:
1. `Ward`
2. `PatientCount`
3. `AvgRiskScore`
4. `HighRiskPatients`
5. `HighRiskSharePct`
6. `MedianCharlsonIndex`
7. `MostCommonAgeBand`
8. `EscalationNeeded`

Ward summary rules:
- `PatientCount`: number of admissions in the ward
- `AvgRiskScore`: mean of `ReadmissionRiskScore`, rounded to 2 decimals
- `HighRiskPatients`: count of rows where `RiskTier = "High"`
- `HighRiskSharePct = HighRiskPatients / PatientCount * 100`, rounded to 1 decimal
- `MedianCharlsonIndex`: median of `CharlsonIndex`, rounded to 1 decimal
- `MostCommonAgeBand`: modal `AgeBand` within the ward; if multiple age bands tie, choose the oldest band using this priority: `80+`, `65-79`, `50-64`, `<50`
- `EscalationNeeded = "Yes"` if `AvgRiskScore >= 10` or `HighRiskPatients >= 2`, otherwise `"No"`

Save the completed workbook in place at `/root/data/readmission_risk_dashboard.xlsx`.
