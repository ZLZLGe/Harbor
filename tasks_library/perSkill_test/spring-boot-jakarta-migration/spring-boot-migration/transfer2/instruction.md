Under the `/workspace/` folder, the user management microservice has already been moved onto Java 21 and Spring Boot 3.2, but one persistence-specific migration pass is still incomplete.

Objective:
- The build still contains Java 8 compiler settings and compatibility dependencies that no longer belong in the Boot 3 line. Remove that debt and return to the target baseline.

Output:
- Write a short migration summary to `/root/transfer2_java8_compat_report.md`.

Success criteria:
1. Run `mvn -q test` successfully.
2. Keep the persistence change scoped to the migration problem described above.
3. Make sure `/root/transfer2_java8_compat_report.md` explains the key Hibernate-facing fixes.
