You are reviewing a short batch of telemetry captures for a branch incident queue.

Inputs available in `/root/`:

1. Packet captures listed in `/root/data/similar_batch_manifest.json`
2. `/root/suricata.yaml`
3. `/root/local.rules`

Create `/root/similar_alert_digest.json`.

Requirements:

1. Process the captures in the same order as the manifest.
2. For each capture, record:
   - `pcap`
   - `site`
   - `alert_count`
   - `signature_ids`
   - `status`
   - `escalation`
3. `signature_ids` must contain the unique alert signature ids seen in that capture, sorted ascending.
4. Set `status` as:
   - `confirmed-exfil` if signature id `1000001` appears
   - `staging-activity` if `1000001` does not appear and `1000002` appears
   - `clean` otherwise
5. Set `escalation` as:
   - `page` for `confirmed-exfil`
   - `review` for `staging-activity`
   - `none` for `clean`
6. The output JSON must have exactly these top-level keys:
   - `batch_id`
   - `results`
   - `totals`
7. `totals` must include:
   - `pcap_count`
   - `alerted_pcaps`
   - `page_count`
   - `total_alerts`
