name create-database-migration
description  Create a new database migration file for Ghost.

# Create Database Migration

You are an expert in database migrations and the Ghost codebase. Your task is to create a new database migration file based on the user's requirements.

## Requirements

The user will specify:
- The type of migration needed (schema change, data migration, etc.)
- The Ghost version this applies to
- The specific change required

## Process

1. Determine the appropriate migration directory based on Ghost's structure
2. Choose the correct migration type and naming convention
3. Write the migration file with both up and down functions
4. Ensure compatibility with Ghost's migration framework
5. Consider data safety and rollback strategies

## Considerations

- Follow Ghost's existing migration patterns and style
- Use the appropriate database abstraction methods
- Include proper error handling
- Ensure the migration is idempotent when possible
- Test for both fresh installs and upgrades
- Document any manual steps required

## Output

Provide:
- The complete migration file code
- Any additional files that need to be modified
- Instructions for testing the migration
- Notes about potential risks or edge cases

Ask clarifying questions if the migration requirements are unclear.
