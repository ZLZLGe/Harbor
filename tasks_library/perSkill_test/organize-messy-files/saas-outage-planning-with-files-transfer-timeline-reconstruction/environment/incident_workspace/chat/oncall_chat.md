# On-call Chat Extract

[2026-02-14 09:15 UTC] Maya (SRE): Paging checkout-api. Latency alert is firing on `/v1/checkout/session`.
[2026-02-14 09:18 UTC] Jin (Backend): Only prod change this morning was release `2026.02.14-rc3`; it enabled synchronous invoice prefetch for the receipt sidebar.
[2026-02-14 09:20 UTC] Leo (Payments): Provider latency warning started after our backlog jumped. Edge auth and payment health checks still look green.
[2026-02-14 09:26 UTC] Maya (SRE): Declaring SEV-1. Impact is checkout failures across web and mobile checkout.
[2026-02-14 09:29 UTC] Jin (Backend): Canary did not trip because the rollout skipped the flag validation step. The prod snapshot now shows `INVOICE_PREFETCH_MODE=sync`.
[2026-02-14 09:31 UTC] Maya (SRE): Turning invoice prefetch off now.
[2026-02-14 09:34 UTC] Maya (SRE): 5xx rate and pool waiters are dropping immediately after the flag disable.
[2026-02-14 09:41 UTC] Jin (Backend): We still need to confirm why the prefetch query held connections for more than 7 seconds.
