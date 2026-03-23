Under the `/workspace/` folder, the user management microservice has already been moved onto Java 21 and Spring Boot 3.2, but one persistence-specific migration pass is still incomplete.

Objective:
- Update the main build definition so the service is aligned with the Boot 3.2 / Java 21 baseline and the modular JWT dependency layout.

Output:
- Write a short migration summary to `/root/similar_boot_build_report.md`.

Success criteria:
1. Run `mvn -q test` successfully.
2. Keep the persistence change scoped to the migration problem described above.
3. Make sure `/root/similar_boot_build_report.md` explains the key Hibernate-facing fixes.
