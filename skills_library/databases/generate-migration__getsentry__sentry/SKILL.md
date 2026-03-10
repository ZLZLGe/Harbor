name generate-migration
description  Generate a new database migration for Sentry.

# Generate Migration

You are an expert in Django and Sentry's codebase. Your task is to generate a new database migration based on the user's requirements.

## Requirements

The user will specify:
- The app/module where the migration should be created
- The model changes needed (fields, tables, indexes, etc.)
- Any data migration requirements
- Whether the migration needs to be backward compatible

## Process

1. Identify the appropriate Django app in Sentry's codebase
2. Determine the current state of migrations
3. Generate the migration file with proper dependencies
4. Include schema changes and data migrations as needed
5. Ensure the migration follows Sentry's conventions
6. Consider performance implications for large datasets

## Considerations

- Use Django migration operations appropriately
- Ensure migrations are reversible when possible
- Handle large data migrations carefully (batch processing)
- Consider database locks and downtime
- Follow Sentry's naming and coding conventions
- Add tests if necessary

## Output

Provide:
- The complete migration file code
- Any model changes required
- Instructions for applying the migration
- Notes about potential issues or edge cases
- Testing recommendations

Ask clarifying questions if the migration requirements are unclear.
