You are helping a research group prepare a submission-readiness evidence packet for a short academic position paper. The draft currently contains mixed-quality citations, duplicated records, and several claims that may be overstated or linked to the wrong source.

Input data is located in `/root/research_packet/`.

The packet contains:
- `/root/research_packet/draft_claims.md`: numbered claims from the draft manuscript.
- `/root/research_packet/seed_library.bib`: a noisy seed bibliography with duplicates, incomplete entries, and possible hallucinated records.
- `/root/research_packet/topic_scope.json`: the allowed research scope, inclusion rules, and exclusion rules.
- `http://127.0.0.1:8765`: a local evidence gateway that serves deterministic scholarly metadata and abstracts from academic-style sources.

Your task:

1. Verify every numbered claim in `draft_claims.md` against the available scholarly evidence.
2. Decide whether each claim is `supported`, `overstated`, `unsupported`, `wrong_citation`, or `out_of_scope`.
3. For claims marked `overstated` or `wrong_citation`, write a corrected version that stays within what the evidence supports.
4. Build a clean bibliography from real, relevant sources only. Remove duplicate, fake, malformed, irrelevant, and unverifiable citations.
5. For every accepted source, write a compact method-and-limitation assessment that identifies the paper's research design, main contribution, methodological limitations, and role in the packet.
6. Write a concise literature note that synthesizes the verified evidence by theme, highlights methodological limitations, and identifies remaining research gaps.

Write all outputs under `/root/answer/`:

```text
/root/answer/evidence_matrix.json
/root/answer/references.bib
/root/answer/literature_note.md
```

`evidence_matrix.json` must use this format:

```json
{
  "claims": [
    {
      "claim_id": "C01",
      "decision": "supported",
      "corrected_claim": null,
      "evidence_keys": ["bib_key_1", "bib_key_2"],
      "rationale": "Brief explanation grounded in the cited evidence."
    }
  ],
  "source_assessments": [
    {
      "bib_key": "bib_key_1",
      "research_design": "Brief description of the paper's design or method.",
      "main_contribution": "Brief description of what the paper contributes to the packet.",
      "methodological_limitations": ["Limitation 1", "Limitation 2"],
      "scope_role": "core_architecture | retrieval_method | generation_method | out_of_scope_context",
      "human_participants": false
    }
  ],
  "rejected_sources": [
    {
      "input_key_or_title": "source key or title from the seed library",
      "reason": "duplicate | fake_or_unverified | irrelevant | malformed | outside_scope"
    }
  ]
}
```

Rules for `evidence_matrix.json`:
- Include every claim from `draft_claims.md` exactly once.
- `claim_id` values must match the claim IDs in the draft.
- `decision` must be one of: `supported`, `overstated`, `unsupported`, `wrong_citation`, `out_of_scope`.
- `corrected_claim` must be `null` for `supported`, `unsupported`, and `out_of_scope` claims.
- `corrected_claim` must be a non-empty string for `overstated` and `wrong_citation` claims.
- `evidence_keys` must refer only to entries present in `/root/answer/references.bib`.
- Include one `source_assessments` item for each accepted bibliography entry.
- `source_assessments[].bib_key` values must refer only to entries present in `/root/answer/references.bib`.
- `scope_role` must be one of: `core_architecture`, `retrieval_method`, `generation_method`, `out_of_scope_context`.
- `human_participants` must be a boolean.
- Do not cite sources that are listed in `rejected_sources`.

`references.bib` must contain only cleaned BibTeX entries for accepted sources:
- Each entry must have a stable citation key.
- Each accepted source must include enough metadata to identify the work: title, authors, year, and either DOI, arXiv ID, URL, or another stable scholarly identifier when available.
- Do not include fake, duplicate, irrelevant, unverifiable, or out-of-scope entries.

`literature_note.md` must use this structure:

```md
## Research Question

## Evidence Synthesis

## Methodological Caveats

## Research Gaps

## References
```

Rules for `literature_note.md`:
- Cite accepted BibTeX keys using bracketed citation keys, for example `[smith2023example]`.
- Do not introduce claims that are not supported by the accepted bibliography.
- In `## Methodological Caveats`, distinguish retrieval-side, generation-side, and evaluation-side limitations.
- Keep the note concise and evidence-focused.

Important constraints:
- Use the provided input files and the local evidence gateway. Do not replace the gateway with a stub, mock, or hard-coded answer path.
- Do not fabricate scholarly sources, citation identifiers, abstracts, or author lists.
- Do not include sources in the final bibliography unless they can be verified from the provided data or the local evidence gateway.
- Do not delete required outputs, skip required claims, or narrow the task by ignoring inconvenient evidence.
- Do not hide answers in filenames, environment variables, logs, or generated helper files.
