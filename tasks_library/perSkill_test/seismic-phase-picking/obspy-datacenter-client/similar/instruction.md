You have a local request list at `/root/data/retrieval_requests.json`.

Create `/root/similar_retrieval_plan.json`.

Requirements:
1. Output valid JSON with exactly two top-level keys: `generated_from` and `plans`.
2. `generated_from` must contain `request_count`.
3. `plans` must be sorted by `request_id`.
4. Each plan entry must contain exactly these keys:
   - `request_id`
   - `strategy_code`
   - `service_family`
   - `client_target`
   - `justification`
5. Use these rules:
   - if `requires_response_archive` is `true`, choose:
     - `strategy_code = "iris_special"`
     - `service_family = "response-format-service"`
     - `client_target = "iris"`
     - `justification = "response-format-special-case"`
   - otherwise choose:
     - `strategy_code = "standard_fdsn"`
     - `service_family = "fdsn-web-services"`
     - `client_target = "fdsn"`
     - `justification = "modern-common-service"`
6. Do not read anything from `/tests`.
