Under the `/workspace/` folder, the user management microservice has already been moved onto Java 21 and Spring Boot 3.2, but one persistence-specific migration pass is still incomplete.

Objective:
- The service and exception-handling layers still carry old persistence and servlet imports. Finish that migration cleanly and keep the user-service behavior intact.

Output:
- Write a short migration summary to `/root/transfer1_service_namespace_report.md`.

Success criteria:
1. Run `mvn -q test` successfully.
2. Keep the persistence change scoped to the migration problem described above.
3. Make sure `/root/transfer1_service_namespace_report.md` explains the key Hibernate-facing fixes.
