---
name: word-redline-workflows
description: Reconcile Word redlines by inventorying tracked changes and comments, then applying accept/reject decisions to produce a clean final DOCX.
---

# Word Redline Workflows

Use this skill when the task is a real Word redline reconciliation workflow rather than plain template filling.

## Use This Skill When

- The input is a `.docx` redline with tracked changes.
- Review comments only expose review references, and the true decision mapping lives in a structured manifest such as `customXml/item1.xml`.
- The required output is a clean `.docx` with revisions resolved and review comments removed.
- A naive `python-docx` rewrite risks flattening structure or ignoring revision/comment XML parts, footnotes, or package-level review metadata.

## Core Workflow

1. Inventory tracked changes, review references, and structured manifest entries before editing.
2. Load the review decision file and map decisions back to comment-linked clauses through `customXml/item1.xml`.
3. Apply accept/reject logic directly to every affected story part, including `document.xml` and `footnotes.xml`.
4. Remove comment references, `comments.xml`, and `w:trackRevisions` from the final package.
5. Update the structured review manifest so package-level metadata matches the resolved output.
6. Re-inventory the output to confirm no `w:ins`, `w:del`, or comment markers remain.

## Useful Commands

Inventory the redline package:

```bash
python3 ~/.codex/skills/word-redline-workflows/scripts/inventory_word_redline.py \
  /app/vendor_addendum_redline.docx
```

Apply the review decisions:

```bash
python3 ~/.codex/skills/word-redline-workflows/scripts/apply_redline_decisions.py \
  --input /app/vendor_addendum_redline.docx \
  --decisions /app/review_decisions.json \
  --output /app/output/vendor_addendum_final.docx
```

## Notes

- Tracked changes live in raw OOXML elements such as `w:ins` and `w:del`; they are not handled safely by high-level paragraph replacement.
- The visible comment text may only contain `Review Ref:` tokens. You may need `customXml/item1.xml` to recover the actual decision key.
- The affected review scope can span more than `word/document.xml`; check `word/footnotes.xml` and `word/settings.xml` too.
- A clean final package should remove comment markers from all affected story parts, remove the `comments.xml` part plus its relationship/content-type entry, and clear package-level pending review metadata.
