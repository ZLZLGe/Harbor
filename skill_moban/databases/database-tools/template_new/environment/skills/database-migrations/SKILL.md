---
name: database-migrations
description: Database migration best practices for schema changes, data migrations, rollbacks, and zero-downtime deployments across PostgreSQL, MySQL, and common ORMs.
origin: ECC
---

# Database Migration Patterns

Safe, reversible database schema changes for production systems.

## When to Activate

- Creating or altering database tables
- Adding or removing columns or indexes
- Running data migrations such as backfills or transforms
- Planning zero-downtime schema changes
- Setting up migration tooling for a new project

## Core Principles

1. **Every change is a migration**. Never alter production databases manually.
2. **Migrations are forward-only in production**. Rollbacks should be planned explicitly.
3. **Schema and data migrations are separate**. Do not mix DDL and DML in one migration.
4. **Test migrations against production-sized data**. Small fixtures do not expose lock behavior.
5. **Migrations are immutable once deployed**. Add new migrations instead of editing applied ones.

## Migration Safety Checklist

Before applying any migration:

- [ ] Migration has both UP and DOWN, or is explicitly marked irreversible
- [ ] No full table locks on large tables
- [ ] New columns have defaults or are nullable
- [ ] Indexes on existing large tables are created with concurrent patterns when needed
- [ ] Data backfill is separate from schema change
- [ ] The migration has been tested against realistic data volume
- [ ] The rollback plan is documented

## PostgreSQL Patterns

### Adding a Column Safely

```sql
ALTER TABLE users ADD COLUMN avatar_url TEXT;

ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;
```

Avoid:

```sql
ALTER TABLE users ADD COLUMN role TEXT NOT NULL;
```

### Adding an Index Without Downtime

Avoid:

```sql
CREATE INDEX idx_users_email ON users (email);
```

Prefer:

```sql
CREATE INDEX CONCURRENTLY idx_users_email ON users (email);
```

### Renaming a Column

Use an expand-contract sequence:

```sql
ALTER TABLE users ADD COLUMN display_name TEXT;
UPDATE users SET display_name = username WHERE display_name IS NULL;
```

Then shift reads and writes before removing the old column.

### Large Data Migrations

Avoid one huge update in a single transaction.

Use batched updates with progress and controlled locking.

## Zero-Downtime Migration Strategy

For critical production changes, follow an expand-contract sequence:

```text
Phase 1: EXPAND
  - Add the new column or table
  - Start dual writes where needed
  - Backfill existing data

Phase 2: MIGRATE
  - Shift reads to the new shape
  - Verify consistency

Phase 3: CONTRACT
  - Remove old writes
  - Drop old columns or tables in a later migration
```

## Anti-Patterns

| Anti-Pattern | Why It Fails | Better Approach |
| --- | --- | --- |
| Manual SQL in production | No audit trail and not repeatable | Always use migration files |
| Editing deployed migrations | Causes drift between environments | Create a new migration |
| `NOT NULL` without default on existing tables | Table rewrites and long locks | Add nullable, backfill, then add the constraint |
| Inline index creation on large tables | Blocks writes | Use concurrent index patterns |
| Schema and data in one migration | Hard to rollback and debug | Separate migrations |
| Dropping a column before application changes | Application errors on missing fields | Remove application dependency first |
