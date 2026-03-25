You have campaign descriptions at `/root/data/campaigns.json`.

Create `/root/transfer2_campaign_strategy.json`.

Requirements:
1. Output valid JSON with exactly two top-level keys: `summary` and `campaigns`.
2. `campaigns` must be sorted by `campaign_id`.
3. Each campaign entry must contain exactly these keys: `campaign_id`, `strategy_code`, `client_target`, `primary_reason`.
4. Use these rules in priority order:
   - if `waveforms_requested >= 500`: `mass_downloader`, `mass-downloader`, `volume`
   - else if `geographic_scope` is `regional` or `multi-region`: `mass_downloader`, `mass-downloader`, `geography`
   - else if `station_count >= 20` and `need_station_metadata` is `true`: `mass_downloader`, `mass-downloader`, `station-bundle`
   - otherwise: `direct_fdsn`, `fdsn`, `small-direct`
5. `summary` must contain `campaign_count`, `mass_downloader_count`, and `direct_fdsn_count`.
6. Do not read anything from `/tests`.
