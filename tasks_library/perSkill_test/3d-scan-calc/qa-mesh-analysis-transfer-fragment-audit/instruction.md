You are reviewing a contaminated binary STL scan from a reverse-engineering QA check at `/root/fragment_audit_scan.stl`.
The scan contains one real assembly plus many disconnected fragments from the capture session.

Read `/root/fragment_cleanliness_policy.md` and write `/root/fragment_audit.json` with this exact schema:

```json
{
  "component_count": 53,
  "fragment_count": 52,
  "fragment_count_ratio": 0.9811320755,
  "main_assembly_volume_cm3": 6242.8903125949,
  "debris_volume_cm3": 344.1792468216,
  "debris_volume_ratio": 0.0522507382,
  "cleanliness_threshold": 0.05,
  "passes_cleanliness_threshold": false
}
```

Requirements:
1. Parse `/root/fragment_audit_scan.stl` as a binary STL.
2. Split the scan into connected components using shared vertices.
3. Treat the largest connected component by volume as the real assembly.
4. The STL coordinates are already in centimeters, so all volumes are in `cm^3`.
5. Compute:
   - `component_count`: total number of connected components.
   - `fragment_count`: `component_count - 1`.
   - `fragment_count_ratio`: `fragment_count / component_count`.
   - `main_assembly_volume_cm3`: volume of the largest component.
   - `debris_volume_cm3`: sum of the volumes of every non-main component.
   - `debris_volume_ratio`: `debris_volume_cm3 / (main_assembly_volume_cm3 + debris_volume_cm3)`.
6. Read the maximum allowed debris-volume ratio from `/root/fragment_cleanliness_policy.md`.
7. Store that decimal ratio in `cleanliness_threshold`.
8. Set `passes_cleanliness_threshold` to `true` when `debris_volume_ratio <= cleanliness_threshold`, otherwise `false`.
9. Write numeric JSON values as numbers, not strings.

Notes:
- Small floating-point error is acceptable.
- The fragment-count ratio is informational; the pass/fail decision uses the debris-volume threshold from the policy file.
