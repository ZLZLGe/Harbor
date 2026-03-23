Under the `/workspace/` folder, the user management microservice has already been moved onto Java 21 and Spring Boot 3.2, but one persistence-specific migration pass is still incomplete.

Objective:
- Finish the namespace sweep across the entity, request DTO, and controller entrypoint so the upgraded service no longer depends on legacy Java EE imports.

Output:
- Write a short migration summary to `/root/similar_namespace_sweep_report.md`.

Success criteria:
1. Run `mvn -q test` successfully.
2. Keep the persistence change scoped to the migration problem described above.
3. Make sure `/root/similar_namespace_sweep_report.md` explains the key Hibernate-facing fixes.
