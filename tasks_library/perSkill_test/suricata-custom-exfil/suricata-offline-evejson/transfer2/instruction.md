You are validating whether a quiet-hours monitoring window stayed within alert budgets across three clinic sites.

Inputs available in `/root/`:

1. `/root/data/transfer2_site_manifest.json`
2. Packet captures referenced by that manifest
3. `/root/suricata.yaml`
4. `/root/local.rules`

Create `/root/transfer2_rule_budget_audit.json`.

Requirements:

1. Process sites in manifest order.
2. For each site, sum the total alert count across all listed captures and record:
   - `site`
   - `captures`
   - `max_allowed_alerts`
   - `observed_alerts`
   - `status`
3. Set `status` to `pass` when `observed_alerts <= max_allowed_alerts`; otherwise set it to `fail`.
4. The output JSON must have exactly these top-level keys:
   - `audit_window`
   - `site_results`
   - `sites_passing`
   - `sites_failing`
   - `highest_volume_site`
5. `sites_passing` and `sites_failing` must preserve the manifest order of sites that land in each bucket.
6. `highest_volume_site` is the site with the largest `observed_alerts`. If there is a tie, use the first site in manifest order among the tied sites.
