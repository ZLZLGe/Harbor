Under `/workspace/` there is a Java 21 user roster service codebase that has already been upgraded to the new platform baseline, but the namespace migration is incomplete.

Repair the remaining legacy Java EE imports so the verification script succeeds:
`bash /workspace/verify.sh`

Then write `/root/similar_namespace_report.json` with this exact JSON structure:
```json
{
  "service": "user-roster",
  "migrated_files": [
    "src/main/java/com/example/roster/controller/UserRosterController.java",
    "src/main/java/com/example/roster/dto/UserSignupRequest.java",
    "src/main/java/com/example/roster/filter/CorrelationIdFilter.java",
    "src/main/java/com/example/roster/model/RosterUser.java"
  ],
  "packages_fixed": [
    "javax.persistence",
    "javax.servlet",
    "javax.validation"
  ],
  "remaining_javax_imports": 0
}
```

Rules:
1. Do not modify `/workspace/verify.sh`.
2. `remaining_javax_imports` counts only `import javax...` statements under `/workspace/src`.
3. The namespace repair must be done in source code, not by changing verifier inputs.
