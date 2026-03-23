Under `/workspace` there is a Java 21 warehouse dock assignment service that was migrated most of the way to Spring Boot 3.2. One persistence entity still uses the old JPA namespace, and the repository query still uses a path expression that needs to be made explicit for the current ORM parser.

Repair the source, then write `/root/transfer1_query_fix.json` with this exact structure:

```json
{
  "service": "warehouse-transfer",
  "updated_query": "select t from TransferOrder t where t.dock.code = :dockCode and t.closed = false order by t.priority desc",
  "touched_files": [
    "src/main/java/com/example/warehouse/model/TransferOrder.java",
    "src/main/java/com/example/warehouse/repository/TransferOrderRepository.java"
  ]
}
```

Rules:
1. Keep the project on Spring Boot 3.2 and Java 21.
2. Do not add external services or extra skills.
3. The repository query must stay a single JPQL statement.
