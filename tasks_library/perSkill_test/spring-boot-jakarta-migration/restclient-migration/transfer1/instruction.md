Under `/workspace`, there is a Spring Boot 3.2 billing bridge application. The HTTP integration in `src/main/java/com/example/billingbridge/client/InvoiceLedgerClient.java` still uses the older template-style client.

Migrate that integration to Spring's modern synchronous HTTP client API while preserving these behaviors:

1. Fetch a single invoice status record from the ledger service
2. Translate upstream 5xx responses into the existing `LedgerUnavailableException`
3. Send an acknowledgement POST for a processed invoice

Constraints:

- Keep the application on Java 21 and Spring Boot 3.2.
- Do not require any live external endpoint during verification.
- Preserve the existing `LedgerUnavailableException` contract.
- Make the project pass `mvn test`.

The main deliverable is the migrated implementation in `/workspace/src/main/java/com/example/billingbridge/client/InvoiceLedgerClient.java`.
