Under the `/workspace/` folder, the user management microservice has already been moved onto Java 21 and Spring Boot 3.2, but one persistence-specific migration pass is still incomplete.

Objective:
- A later API-layer refactor reintroduced legacy namespace imports around validation and servlet request handling. Clean those up without broadening the task into other migration areas.

Output:
- Write a short migration summary to `/root/transfer2_api_edge_namespace_report.md`.

Success criteria:
1. Run `mvn -q test` successfully.
2. Keep the persistence change scoped to the migration problem described above.
3. Make sure `/root/transfer2_api_edge_namespace_report.md` explains the key Hibernate-facing fixes.
