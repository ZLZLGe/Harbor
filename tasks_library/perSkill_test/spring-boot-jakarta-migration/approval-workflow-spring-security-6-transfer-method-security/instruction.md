Under `/workspace` there is a Spring Boot 3.2 document approval workflow service. The controllers, workflow policy bean, and test users already reflect the expected access model, but `/workspace/src/main/java/com/example/approval/security/MethodSecurityConfig.java` still uses the removed adapter-style and global method-security setup, so the project no longer builds.

Update that configuration so the workflow keeps its current behavior:

- `GET /actuator/health` stays public.
- All approval API routes continue to require HTTP Basic authentication.
- Method-level authorization must remain active for the existing SpEL rules:
  - a submitter can view and resubmit only their own document,
  - an approver can record a decision only for the document assigned to them,
  - a supervisor can view or decide any document.
- Keep the authentication wiring compatible with the existing in-memory user directory and password encoding.

Keep the change focused on the security migration. The primary output is:

`/workspace/src/main/java/com/example/approval/security/MethodSecurityConfig.java`

Validation command:

`mvn test`
