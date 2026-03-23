You are comparing a current detection package and a candidate package against the same capture batch.

Inputs available in `/root/`:

1. `/root/data/transfer3_capture_manifest.json`
2. Packet captures referenced by that manifest
3. `/root/suricata.yaml`
4. `/root/rules/current.rules`
5. `/root/rules/candidate.rules`

Create `/root/transfer3_rule_regression_report.json`.

Requirements:

1. Process captures in manifest order.
2. For each capture, record:
   - `pcap`
   - `owner`
   - `current_alert_count`
   - `candidate_alert_count`
   - `current_signature_ids`
   - `candidate_signature_ids`
   - `new_signature_ids`
   - `regression_flag`
3. All signature id arrays must contain unique ids sorted ascending.
4. `new_signature_ids` is the set difference `candidate_signature_ids - current_signature_ids`.
5. Set `regression_flag` to `expanded` if `new_signature_ids` is non-empty; otherwise set it to `unchanged`.
6. The output JSON must have exactly these top-level keys:
   - `comparison_id`
   - `results`
   - `candidate_only_signatures`
   - `pcaps_with_new_alerts`
   - `safe_to_promote`
7. `candidate_only_signatures` must be the unique sorted union of every `new_signature_ids` array.
8. `pcaps_with_new_alerts` must list the capture names with non-empty `new_signature_ids`, preserving manifest order.
9. Set `safe_to_promote` to `true` only when there are no new signature ids on any capture.
