Under `/workspace` there is a Java 21 vendor onboarding service that already targets Spring Boot 3.2, but its profile entity metadata still relies on removed legacy Hibernate type annotations and the old persistence namespace.

Repair the source, then write `/root/transfer3_metadata_mapping_report.md` with exactly this content:

```markdown
# Vendor Metadata Mapping Migration
- service: vendor-onboarding
- removed_annotations: @TypeDef, @Type
- replacement: @JdbcTypeCode(SqlTypes.JSON)
- touched_file: src/main/java/com/example/vendor/model/VendorProfile.java
```

Rules:
1. Use a Hibernate 6-compatible replacement for the legacy type mapping annotations.
2. Do not add external services or extra skills.
3. Keep the report lines and ordering exactly as shown.
