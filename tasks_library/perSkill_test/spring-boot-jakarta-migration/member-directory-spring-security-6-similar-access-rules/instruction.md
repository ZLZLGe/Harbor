Under `/workspace` there is a Spring Boot 3.2 member directory service. The rest of the application already expects the current security model, but `/workspace/src/main/java/com/example/memberdirectory/config/SecurityConfig.java` still uses the removed adapter-based configuration and the project no longer builds.

Update the security configuration so that the service works again without changing the required access rules:

- `POST /api/members/register` stays public.
- `POST /api/session/login` stays public and the injected `AuthenticationManager` in `SessionController` must continue to work.
- `GET /actuator/health` stays public.
- All other endpoints require authentication.
- Method-level security must remain active so that the existing controller annotations continue to enforce:
  - administrators can manage any member,
  - reviewers can read any member and update review status,
  - a normal member can only read their own entry.

Keep the solution focused on the security migration. The primary output is:

`/workspace/src/main/java/com/example/memberdirectory/config/SecurityConfig.java`

Validation command:

`mvn test`
