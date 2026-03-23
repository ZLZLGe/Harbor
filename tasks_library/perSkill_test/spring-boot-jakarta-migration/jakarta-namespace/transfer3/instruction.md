Under the `/workspace/` folder, the user management microservice has already been moved onto Java 21 and Spring Boot 3.2, but one persistence-specific migration pass is still incomplete.

Objective:
- Finish a mixed namespace sweep. Update the remaining Java EE imports, but do not rewrite JDK `javax.crypto` usage that still belongs to the standard library.

Output:
- Write a short migration summary to `/root/transfer3_namespace_guardrail_report.md`.

Success criteria:
1. Run `mvn -q test` successfully.
2. Keep the persistence change scoped to the migration problem described above.
3. Make sure `/root/transfer3_namespace_guardrail_report.md` explains the key Hibernate-facing fixes.
