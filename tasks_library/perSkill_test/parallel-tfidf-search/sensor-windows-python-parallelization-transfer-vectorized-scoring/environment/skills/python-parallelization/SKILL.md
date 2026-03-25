---
name: python-parallelization
description: Transform sequential Python code into parallel/concurrent implementations. Use when asked to parallelize Python code, improve code performance through concurrency, convert loops to parallel execution, or identify parallelization opportunities. Handles CPU-bound (multiprocessing), I/O-bound (asyncio, threading), and data-parallel (vectorization) scenarios.
---

# Python Parallelization Skill

Transform sequential Python code to leverage parallel and concurrent execution patterns.

## Workflow

1. **Analyze** the code to identify parallelization candidates
2. **Classify** the workload type (CPU-bound, I/O-bound, or data-parallel)
3. **Select** the appropriate parallelization strategy
4. **Transform** the code with proper synchronization and error handling
5. **Verify** correctness and measure expected speedup

## Parallelization Decision Tree

```
Is the bottleneck CPU-bound or I/O-bound?

CPU-bound (computation-heavy):
├── Independent iterations? → multiprocessing.Pool / ProcessPoolExecutor
├── Shared state needed? → multiprocessing with Manager or shared memory
├── NumPy/Pandas operations? → Vectorization first, then consider numba/dask
└── Large data chunks? → chunked processing with Pool.map

I/O-bound (network, disk, database):
├── Many independent requests? → asyncio with aiohttp/aiofiles
├── Legacy sync code? → ThreadPoolExecutor
├── Mixed sync/async? → asyncio.to_thread()
└── Database queries? → Connection pooling + async drivers

Data-parallel (array/matrix ops):
├── NumPy arrays? → Vectorize, avoid Python loops
├── Pandas DataFrames? → Use built-in vectorized methods
├── Large datasets? → Dask for out-of-core parallelism
└── GPU available? → Consider CuPy or JAX
```
