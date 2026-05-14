# Project Brief

Current Grid needs a coordinated content pack built from the bundled North America power snapshot. Keep the writing evidence-led, brisk, and useful for readers who track energy operations and strategy.

```json
{
  "campaign_slug": "north-america-power-mix",
  "publisher": "Current Grid",
  "audience": "Energy strategy and operations readers who want concise, evidence-led takeaways.",
  "primary_angle": "North America's latest power picture splits three ways: Canada is the clean-share outlier, Mexico is still anchored to gas, and the United States moves at unmatched clean-power scale.",
  "required_claims_by_output": {
    "core_angle.md": [
      "C03_CANADA_CLEAN_SHARE",
      "C05_MEXICO_GAS_RELIANCE",
      "C07_US_CLEAN_SCALE"
    ],
    "x_thread.md": [
      "C03_CANADA_CLEAN_SHARE",
      "C04_CANADA_HYDRO_LEAD",
      "C05_MEXICO_GAS_RELIANCE",
      "C06_MEXICO_LOWEST_CO2",
      "C07_US_CLEAN_SCALE"
    ],
    "linkedin_post.md": [
      "C03_CANADA_CLEAN_SHARE",
      "C05_MEXICO_GAS_RELIANCE",
      "C07_US_CLEAN_SCALE"
    ],
    "newsletter.md": [
      "C02_US_GDP_SCALE",
      "C03_CANADA_CLEAN_SHARE",
      "C05_MEXICO_GAS_RELIANCE",
      "C06_MEXICO_LOWEST_CO2",
      "C07_US_CLEAN_SCALE"
    ],
    "short_video_script.md": [
      "C03_CANADA_CLEAN_SHARE",
      "C05_MEXICO_GAS_RELIANCE",
      "C06_MEXICO_LOWEST_CO2",
      "C07_US_CLEAN_SCALE"
    ]
  },
  "platform_rules": {
    "core_angle.md": "A short strategy note with a clear primary angle, an audience hook, and the claim ids in scope.",
    "x_thread.md": "Five numbered posts. One claim focus per post. No hashtags.",
    "linkedin_post.md": "Start with a headline, then a single post body with short paragraphs.",
    "newsletter.md": "Include Subject: and Preview:, then an intro, three short sections, and a closing CTA.",
    "short_video_script.md": "Six numbered beats. Every beat must include Visual: and Line:."
  },
  "source_files": [
    "brief/project_brief.md",
    "brief/source_packet.md",
    "data/claim_catalog.json",
    "data/country_profile.json",
    "data/world_bank_population.json",
    "data/world_bank_gdp.json",
    "data/annual_co2_emissions.csv",
    "data/electricity_prod_source.csv"
  ],
  "banned_phrases": [
    "game-changer",
    "revolutionary",
    "in today's rapidly evolving landscape"
  ]
}
```

Publisher notes

- Open with the comparison, then move to the implication.
- Keep the tone explanatory, not slogan-heavy.
- Use claim ids in the manifest only. The public-facing drafts should read cleanly without inline claim tags.
- Keep the CTA modest and useful.
