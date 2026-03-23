Under `/workspace`, there is a Spring Boot 3.2 compliance archive application. It still exposes a legacy synchronous HTTP bean in `src/main/java/com/example/compliancearchive/config/ComplianceRestClientConfig.java`, and the business client in `src/main/java/com/example/compliancearchive/client/ComplianceArchiveClient.java` depends on that older template-style API.

Modernize this integration by introducing a shared `RestClient` bean and migrating the archive client to use it. Preserve these behaviors:

1. Archive a case with a JSON POST request
2. Fetch archive status with a GET request
3. Keep the compliance base URL configurable from properties
4. Preserve the default request headers that identify the compliance source

Constraints:

- Keep the application on Java 21 and Spring Boot 3.2.
- Do not require any external service during verification.
- The archive client should use the shared configured bean instead of constructing its own client.
- Make the project pass `mvn test`.

The main deliverable is the migrated configuration in `/workspace/src/main/java/com/example/compliancearchive/config/ComplianceRestClientConfig.java`, together with any necessary updates to the archive client.
