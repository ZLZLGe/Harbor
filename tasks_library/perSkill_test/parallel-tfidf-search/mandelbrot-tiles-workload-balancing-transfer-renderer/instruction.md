# Transfer: Mandelbrot Tile Renderer

In `/root/workspace/`, there is a sequential Mandelbrot renderer used for exporting grayscale zoom plates as rectangular image tiles.

Some tiles fall mostly in empty background and finish quickly, while tiles that cross the Mandelbrot boundary can consume far more iterations. A naive fixed split leaves late tiles straggling, so the parallel version needs to stay pixel-perfect while keeping workers busier on these uneven regions.

Write your solution in `/root/workspace/mandelbrot_balance_solution.py`. Your code must implement:

1. `render_mandelbrot_parallel(scene, num_workers=None, tile_rows=24, tile_cols=24)`
   Return a `ParallelRenderResult` whose `image` matches the sequential `MandelbrotImage` structure from the workspace.

Requirements:

- Match the sequential renderer exactly for every pixel intensity and image metadata.
- Keep output deterministic for the same scene even if tiles finish in a different internal order.
- Improve throughput on the provided boundary-heavy scene with 4 workers.
- The verifier will compare your output against the sequential implementation in the workspace.
