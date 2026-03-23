Under the `/workspace/` folder, the user management microservice has already been moved onto Java 21 and Spring Boot 3.2, but one persistence-specific migration pass is still incomplete.

Objective:
- One more security refactor left exception handling and header configuration on the old chained API. Move those pieces onto the Spring Security 6 style without changing the endpoint contract.

Output:
- Write a short migration summary to `/root/transfer3_security_exception_report.md`.

Success criteria:
1. Run `mvn -q test` successfully.
2. Keep the persistence change scoped to the migration problem described above.
3. Make sure `/root/transfer3_security_exception_report.md` explains the key Hibernate-facing fixes.
