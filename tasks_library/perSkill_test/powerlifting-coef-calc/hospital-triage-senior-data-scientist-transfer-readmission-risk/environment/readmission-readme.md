# Readmission Risk Dashboard Data Notes

`Admissions` contains one row per inpatient admission intake.

Columns:
- `AdmissionID`: unique encounter identifier
- `Ward`: receiving inpatient ward
- `Age`: patient age in years at admission
- `PriorAdmissions90D`: number of inpatient admissions in the last 90 days
- `HeartRate`: beats per minute at intake
- `SystolicBP`: systolic blood pressure in mmHg
- `RespiratoryRate`: breaths per minute
- `OxygenSaturation`: pulse oximetry percent
- `TemperatureC`: body temperature in Celsius
- `CharlsonIndex`: comorbidity burden index
- `HasCOPD`: 1 if chronic obstructive pulmonary disease is documented, else 0
- `HasCHF`: 1 if congestive heart failure is documented, else 0
- `HasDiabetes`: 1 if diabetes is documented, else 0
- `HasCKD`: 1 if chronic kidney disease is documented, else 0

The two empty worksheets are reserved for your outputs:
- `RiskScoring`: patient-level engineered features and risk tiers
- `WardSummary`: ward-level rollup for triage prioritization
