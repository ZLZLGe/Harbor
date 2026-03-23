Under the `/workspace/` folder, the user management microservice has already been moved onto Java 21 and Spring Boot 3.2, but one persistence-specific migration pass is still incomplete.

Objective:
- The project already moved part of the way onto Boot 3, but the build still carries an older Java target and legacy JWT/JAXB dependencies. Finish the modernization cleanly.

Output:
- Write a short migration summary to `/root/transfer1_partial_boot_upgrade_report.md`.

Success criteria:
1. Run `mvn -q test` successfully.
2. Keep the persistence change scoped to the migration problem described above.
3. Make sure `/root/transfer1_partial_boot_upgrade_report.md` explains the key Hibernate-facing fixes.
