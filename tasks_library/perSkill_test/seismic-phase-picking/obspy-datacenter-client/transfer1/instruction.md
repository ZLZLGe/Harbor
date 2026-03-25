You have a routing request table at `/root/data/routing_requests.csv`.

Create `/root/transfer1_routing_matrix.csv`.

Requirements:
1. Preserve the input row order.
2. Write exactly these columns: `request_id`, `strategy_code`, `routing_service`, `client_target`, `why`.
3. Use these rules:
   - if `datacenter_hint` is not empty: `direct_fdsn`, `none`, `fdsn`, `known-provider`
   - else if `region_code` is `EU`: `route_then_fdsn`, `eidaws-routing`, `fdsn`, `unknown-provider-eu`
   - otherwise: `route_then_fdsn`, `iris-federator`, `fdsn`, `unknown-provider-global`
4. Do not read anything from `/tests`.
