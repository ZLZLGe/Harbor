You are preparing a routed queue for four capture-backed investigations.

Inputs available in `/root/`:

1. Packet captures referenced by `/root/data/transfer1_ticket_manifest.json`
2. `/root/data/transfer1_score_weights.json`
3. `/root/suricata.yaml`
4. `/root/local.rules`

Create `/root/transfer1_incident_queue.csv`.

Requirements:

1. Process every manifest ticket.
2. For each ticket, compute:
   - `ticket_id`
   - `pcap`
   - `owner`
   - `environment`
   - `alert_count`
   - `signature_ids`
   - `weighted_score`
   - `queue_status`
3. `signature_ids` must be the unique signature ids seen in that capture, sorted ascending and joined by `|`. Use an empty string if there are no alerts.
4. `weighted_score` is the sum of per-alert weights from `transfer1_score_weights.json`. Unknown signature ids count as `0`.
5. Set `queue_status` as:
   - `critical` if `weighted_score >= 12`
   - `review` if `weighted_score >= 1` and `< 12`
   - `clear` if `weighted_score == 0`
6. The CSV header must be exactly:
   - `ticket_id,pcap,owner,environment,alert_count,signature_ids,weighted_score,queue_status`
7. Sort rows by descending `weighted_score`, then ascending `ticket_id`.
