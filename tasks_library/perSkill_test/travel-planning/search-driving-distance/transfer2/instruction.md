You are checking whether same-day site hops can be completed by ground in the Southeast region.

Input file in `/root/data/`:
1. `transfer2_site_hops.tsv`

Produce this file in `/root/`:
1. `transfer2_site_hop_memo.md`

Requirements:
1. Use the bundled city-to-city ground-distance lookup instead of memory.
2. Use driving mode for every lane.
3. Classify a lane as feasible when the looked-up duration is less than or equal to `max_duration_minutes`.
4. Write a markdown file with exactly this section structure:
   - `# Southeast Site-Hop Feasibility`
   - `## Feasible`
   - `## Infeasible`
5. Under `## Feasible`, add one bullet per feasible lane in the format:
   - `- <lane_id> | <origin> -> <destination> | <duration_minutes> min | margin +<minutes>`
6. Under `## Infeasible`, add one bullet per infeasible lane in the format:
   - `- <lane_id> | <origin> -> <destination> | <duration_minutes> min | margin <negative_minutes>`
7. Sort feasible bullets by margin descending, breaking ties by `lane_id`.
8. Sort infeasible bullets by absolute margin ascending, breaking ties by `lane_id`.
9. End the file with these lines in this order:
   - `feasible_count: <count>`
   - `infeasible_count: <count>`
   - `tool_called: <bundled lookup tool used>`
