Under the `/workspace/` folder, the user management microservice has already been moved onto Java 21 and Spring Boot 3.2, but one persistence-specific migration pass is still incomplete.

Objective:
- A later cleanup removed a required starter and reintroduced legacy JWT wiring. Restore the complete Boot 3 dependency alignment without touching unrelated application code.

Output:
- Write a short migration summary to `/root/transfer3_dependency_alignment_report.md`.

Success criteria:
1. Run `mvn -q test` successfully.
2. Keep the persistence change scoped to the migration problem described above.
3. Make sure `/root/transfer3_dependency_alignment_report.md` explains the key Hibernate-facing fixes.
