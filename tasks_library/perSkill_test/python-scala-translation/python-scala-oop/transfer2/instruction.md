## Task Description

`/app/workspace/payments_source.py` models payment types with reusable behaviors.

Create `/app/workspace/transfer2.scala` that translates this design into idiomatic Scala 2.13.

Requirements:

1. Keep a base payment abstraction for amount handling.
2. Map reusable Python mixin behavior into Scala trait composition.
3. Keep concrete payment types with clear overridden/implemented methods.
4. Provide a companion-object style constructor/factory path for creating payment types from string keys.
5. Keep method naming and structure readable for maintainers.
