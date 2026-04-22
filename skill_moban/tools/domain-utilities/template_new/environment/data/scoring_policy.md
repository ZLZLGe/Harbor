# Scoring Policy

Use this policy to evaluate each candidate domain.

## Required sources

- `candidate_domains.csv`
- `authority_metrics.csv`
- `sales_comps.csv`
- `trademark_flags.csv`
- `archive_summaries/*.md`
- local snapshot service documented in `service_catalog.md`

## Archive relevance bonus

- `strong` => `12`
- `medium` => `7`
- `weak` => `2`
- `mismatch` => `-4`

## Market fit

`market_fit_score = keyword_alignment + tone_fit + memorability + brevity_bonus`

All four terms come from `candidate_domains.csv`.

## Authority

`authority_score = min(referring_domains / 5, 18) + trust_signal_score + continuity_bonus + archive_relevance_bonus - link_risk_penalty`

Base authority fields come from `authority_metrics.csv`.
Archive relevance bonus comes from the corresponding file under `archive_summaries/`.

## Commercial intent

`commercial_intent_score = buyer_intent_score + type_in_score + liquidity_bonus + landing_bonus`

Inputs:

- `buyer_intent_score` from `candidate_domains.csv`
- `type_in_score` from `authority_metrics.csv`
- `liquidity_bonus` from local snapshot `listing_state`
- `landing_bonus` from local snapshot `landing_style`

Liquidity bonus mapping:

- `fixed-price` => `8`
- `make-offer` => `6`
- `brokered` => `4`
- `parked` => `2`

Landing bonus mapping:

- `operator-marketplace` => `6`
- `lead-gen` => `5`
- `brandable-inventory` => `4`
- `parked` => `1`

## Legal risk

`legal_risk_score = exact_mark_hits * 16 + similarity_hits * 8 + restricted_term_hits * 5 + confusion_flag_bonus`

Inputs come from `trademark_flags.csv`.

`confusion_flag_bonus` is `6` when `confusion_flag` is `true`, otherwise `0`.

## Total score

`total_score = market_fit_score + authority_score + commercial_intent_score - legal_risk_score`

Round all numeric scores to 2 decimals at the final output stage.

## Price ceiling

1. Find the median `sale_price_usd` in `sales_comps.csv` for the candidate's `comp_family`.
2. Apply:

`price_ceiling_usd = comp_median * market_multiplier * authority_multiplier * liquidity_multiplier * risk_discount * archive_discount`

Where:

- `market_multiplier = 0.65 + market_fit_score / 180`
- `authority_multiplier = 0.72 + authority_score / 220`
- `liquidity_multiplier`:
  - `fixed-price` => `1.03`
  - `make-offer` => `1.00`
  - `brokered` => `0.96`
  - `parked` => `0.80`
- `risk_discount = max(0.50, 1 - legal_risk_score / 100)`
- `archive_discount`:
  - `strong` => `1.00`
  - `medium` => `0.92`
  - `weak` => `0.80`
  - `mismatch` => `0.55`

Round `price_ceiling_usd` to 2 decimals.

## Status rules

- `reject` if any of the following is true:
  - `legal_risk_score >= 20`
  - archive relevance band is `mismatch`
  - local snapshot `rdap_status != "registered"`
  - `total_score < 75`
- `buy_now` if all of the following are true:
  - not already `reject`
  - `total_score >= 100`
  - `legal_risk_score <= 18`
  - `asking_price_usd <= price_ceiling_usd`
  - archive relevance band is `strong` or `medium`
- otherwise `monitor`

## Allowed reason codes

- `STRONG_MARKET_FIT`
- `HIGH_TRUST_SIGNALS`
- `ARCHIVE_TOPIC_MATCH`
- `WEAK_ARCHIVE_RELEVANCE`
- `ARCHIVE_MISMATCH`
- `PRICE_WITHIN_CEILING`
- `ASKING_PRICE_ABOVE_CEILING`
- `TRADEMARK_COLLISION`
- `SIMILARITY_WARNING`
- `TYPE_IN_POTENTIAL`
- `PARKED_LANDING`

## Reason code mapping guidance

Use the following canonical mappings when the corresponding condition is true:

- Include `STRONG_MARKET_FIT` when `market_fit_score >= 50`.
- Include `HIGH_TRUST_SIGNALS` when `authority_score >= 30`.
- Include `ARCHIVE_TOPIC_MATCH` when archive relevance band is `strong` or `medium`.
- Include `WEAK_ARCHIVE_RELEVANCE` when archive relevance band is `weak`.
- Include `ARCHIVE_MISMATCH` when archive relevance band is `mismatch`.
- Include `TRADEMARK_COLLISION` when `legal_risk_score >= 20`.
- Include `SIMILARITY_WARNING` when `0 < legal_risk_score < 20`.
- Include `PRICE_WITHIN_CEILING` when `price_ceiling_usd` is not null and `asking_price_usd <= price_ceiling_usd`.
- Include `ASKING_PRICE_ABOVE_CEILING` when `price_ceiling_usd` is not null and `asking_price_usd > price_ceiling_usd`.
- Include `TYPE_IN_POTENTIAL` when `type_in_score >= 7`.
- Include `PARKED_LANDING` when local snapshot `landing_style == "parked"`.
