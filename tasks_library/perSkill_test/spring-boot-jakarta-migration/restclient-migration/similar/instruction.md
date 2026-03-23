Under `/workspace`, there is a Spring Boot 3.2 customer profile application that still uses a legacy synchronous HTTP client in `src/main/java/com/example/customerprofile/client/ProfileGatewayClient.java`.

Update that client so the codebase uses Spring's modern synchronous HTTP client API instead of the older template-based one. Preserve the existing behavior for:

1. Fetching a customer profile with a GET request
2. Sending a welcome notification with a JSON POST request
3. Deleting an exported profile snapshot with a DELETE request

Constraints:

- Keep the application on Java 21 and Spring Boot 3.2.
- Do not add any external API dependency or require network access during tests.
- Keep the base URL configurable from `application.properties`.
- Make the project pass `mvn test`.

The main deliverable is the migrated implementation in `/workspace/src/main/java/com/example/customerprofile/client/ProfileGatewayClient.java`.
