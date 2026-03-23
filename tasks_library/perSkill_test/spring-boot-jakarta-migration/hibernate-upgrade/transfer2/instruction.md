Under `/workspace` there is a Java 21 incident review service that was almost migrated to Spring Boot 3.2. The remaining blocker is a custom repository implementation that still uses the removed legacy Hibernate Criteria API, plus one entity that still imports the old persistence namespace.

Repair the source, then write `/root/transfer2_criteria_migration.txt` with exactly these four lines:

```text
service=incident-review
replaced_api=org.hibernate.Criteria
new_api=jakarta.persistence.criteria.CriteriaBuilder
query_method=findOpenCasesByTeam
```

Rules:
1. Keep the repository search implemented with JPA Criteria classes.
2. Do not add external services or extra skills.
3. Remove the old Hibernate Criteria imports from the custom repository implementation.
