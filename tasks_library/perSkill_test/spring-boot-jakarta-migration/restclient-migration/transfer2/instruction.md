Under `/workspace`, there is a Spring Boot 3.2 logistics quoting application. The client in `src/main/java/com/example/logisticsquotes/client/CarrierQuoteClient.java` still uses the older template-based synchronous HTTP API.

Migrate that client to Spring's newer synchronous HTTP client API while preserving:

1. Quote lookup with query parameters for origin, destination, and package weight
2. Deserialization of a generic list response containing `CarrierQuote` records
3. Cancellation of a quote request through a DELETE call

Constraints:

- Keep the application on Java 21 and Spring Boot 3.2.
- Do not rely on any live external endpoint during tests.
- Preserve the `CarrierQuote` response shape.
- Make the project pass `mvn test`.

The main deliverable is the migrated implementation in `/workspace/src/main/java/com/example/logisticsquotes/client/CarrierQuoteClient.java`.
