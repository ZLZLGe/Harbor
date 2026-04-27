You are preparing a source-derived brand voice and launch content pack for a content operations team. The team has cached source material from public pages, historical launch notes, product docs, social posts, and customer email drafts; the local content archive service mirrors the same material and must be checked before you write the final pack.

Input data is in `/root/brandroom/input/`:

- `source_manifest.json`: local archive service URL and cache metadata.
- `source_corpus.jsonl`: cached source samples with `source_id`, `title`, `url`, `channel`, `published_at`, and `text`.
- `campaign_brief.json`: audience, product facts, forbidden claims, and campaign constraints.
- `allowed_claims.csv`: claim IDs, approved facts, and evidence sources.
- `channel_specs.json`: required channel formats and length constraints.
- `glossary.json`: preferred terms, banned terms, and replacements.

Your task:

1. Read the cached input files and confirm the local content archive service from `source_manifest.json` is reachable. If it is not already running, start it with `start-brandroom-archive`, then fetch the archive endpoints listed in the manifest.
2. Build a reusable, source-backed brand voice profile. If a brand-voice workflow or schema is available in the environment, use it as the operational method for source priority, named hard-ban taxonomy, anti-pattern extraction, and downstream reuse; otherwise infer the method from the input materials. Extract operational writing rules about rhythm, compression, claim style, evidence habits, formatting habits, lexicon, and hard bans. Exclude non-canonical comparator samples such as generic platform examples, old discarded brand voice, or competitor copy if they appear in the archive.
3. Generate platform-specific content for all required channels:
   - `launch_blog_opening`
   - `linkedin_post`
   - `x_thread`
   - `customer_email`
   - `changelog_note`
4. Each content item must cite at least two real source anchors and at least one approved claim ID when it makes a factual product claim.
5. Produce an audit report showing which sources and claims were used, which risky claims were rejected, which banned phrases were removed, and whether every channel constraint was checked.

Output format:

Create exactly these files under `/root/brandroom/output/`.

`voice_profile.json`

```json
{
  "profile_name": "string",
  "source_inventory": [
    {
      "source_id": "string",
      "title": "string",
      "url": "string",
      "channel": "string",
      "used_for": ["rhythm", "claims", "structure", "lexicon"]
    }
  ],
  "source_priority_applied": [
    {
      "priority": "recent_social_posts | articles_memos_launch_notes | outbound_email | docs_changelog_site_copy",
      "source_ids": ["source_id"],
      "why_used": "string"
    }
  ],
  "excluded_sources": [
    {
      "source_id": "string",
      "reason": "string"
    }
  ],
  "style_profile": {
    "sentence_rhythm": {
      "summary": "string",
      "rules": ["string"]
    },
    "claim_style": ["string"],
    "evidence_habits": ["string"],
    "formatting_habits": ["string"],
    "lexicon": {
      "preferred_terms": ["string"],
      "terms_to_avoid": ["string"],
      "replacement_terms": [
        {
          "avoid": "string",
          "use": "string"
        }
      ]
    },
    "hard_bans": ["string"]
  },
  "do_dont_rules": [
    {
      "do": "string",
      "dont": "string",
      "source_evidence": ["source_id"]
    }
  ],
  "confidence_notes": ["string"]
}
```

`content_pack.json`

```json
{
  "campaign_name": "string",
  "core_angle": "string",
  "items": [
    {
      "channel": "launch_blog_opening",
      "audience": "string",
      "draft": "string",
      "source_anchors": ["string"],
      "allowed_claim_ids": ["string"],
      "voice_profile_rules_used": ["string"],
      "notes": "string"
    },
    {
      "channel": "linkedin_post",
      "audience": "string",
      "draft": "string",
      "source_anchors": ["string"],
      "allowed_claim_ids": ["string"],
      "voice_profile_rules_used": ["string"],
      "notes": "string"
    },
    {
      "channel": "x_thread",
      "audience": "string",
      "posts": ["string"],
      "source_anchors": ["string"],
      "allowed_claim_ids": ["string"],
      "voice_profile_rules_used": ["string"],
      "notes": "string"
    },
    {
      "channel": "customer_email",
      "audience": "string",
      "subject": "string",
      "preview_text": "string",
      "draft": "string",
      "source_anchors": ["string"],
      "allowed_claim_ids": ["string"],
      "voice_profile_rules_used": ["string"],
      "notes": "string"
    },
    {
      "channel": "changelog_note",
      "audience": "string",
      "draft": "string",
      "source_anchors": ["string"],
      "allowed_claim_ids": ["string"],
      "voice_profile_rules_used": ["string"],
      "notes": "string"
    }
  ]
}
```

`audit_report.json`

```json
{
  "files_created": ["voice_profile.json", "content_pack.json", "audit_report.json"],
  "sources_read": ["source_id"],
  "claims_used": ["claim_id"],
  "claims_rejected": [
    {
      "claim": "string",
      "reason": "string"
    }
  ],
  "banned_phrases_removed": ["string"],
  "channel_constraints_checked": [
    {
      "channel": "string",
      "status": "pass",
      "notes": "string"
    }
  ],
  "final_quality_notes": ["string"]
}
```

Notes:

- Do not invent customers, numbers, integrations, certifications, compliance guarantees, performance claims, market rankings, or any product fact that is not present in `allowed_claims.csv` or the approved brief.
- Do not use generic AI marketing phrases such as "In today's rapidly evolving landscape", "game-changing", "revolutionary", "excited to announce", "unlock your potential", or bait-question LinkedIn endings.
- Do not flatten every channel into the same voice. Keep the same source-derived voice while adapting structure to each channel.
- Do not modify `/root/brandroom/input/`, the local archive service, tests, verifier, environment configuration, or skill files.
- Do not replace the real input chain, fabricate source IDs, hard-code verifier expectations, create empty placeholder outputs, delete required functionality, or bypass the content archive service health check.
- Do not call external LLM APIs.
