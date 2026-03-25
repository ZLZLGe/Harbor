# Advanced Techniques

- Prefer NumPy vectorization before introducing process-based parallelism for numeric workloads.
- Use chunked array processing when the full working set would become too large for memory.
- Preserve ordering when replacing sequential loops so downstream consumers keep stable semantics.
- Benchmark the transformed code against the baseline on the actual task inputs instead of relying on intuition.
