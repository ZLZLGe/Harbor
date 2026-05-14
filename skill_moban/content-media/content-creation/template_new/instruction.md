You need to turn a public research packet about North America's electricity mix into a coordinated content pack for a data publisher.

Input data is available under `/app/input/`.

- `brief/project_brief.md`: the delivery contract, audience, publisher notes, and required claim coverage by output.
- `brief/source_packet.md`: the local research packet compiled from the bundled data snapshot.
- `data/country_profile.json`: country metadata.
- `data/world_bank_population.json`: population series.
- `data/world_bank_gdp.json`: GDP series.
- `data/annual_co2_emissions.csv`: emissions series.
- `data/electricity_prod_source.csv`: electricity source mix series.
- `data/claim_catalog.json`: claim ids, source pointers, and evidence notes for the bundled fact set.
- `voice_samples/*.md`: sample publisher copy for tone and pacing.
- `/app/workspace/build_content_pack.py`: the current local build entrypoint. It must remain the formal generation entrypoint for this delivery.

Your tasks

1. Complete the content pack and write the required deliverables to `/app/output/`.
2. Use `project_brief.md` as the delivery contract for output coverage, output order, and platform requirements.
3. Use only claims supported by the bundled input files. Keep the claim mapping in `manifest.json` aligned with the delivered drafts.
4. Keep the local build entrypoint usable so the team can regenerate the same content pack from the current inputs.
5. Clean the outputs so they are ready for review. Do not leave placeholder text, sample filler, review residue, `TODO`, `TBD`, or process commentary in the final deliverables.

Output

- Update the formal delivery code and any necessary supporting configuration under `/app/workspace/`.
- Create exactly these files under `/app/output/`:
  - `core_angle.md`
  - `x_thread.md`
  - `linkedin_post.md`
  - `newsletter.md`
  - `short_video_script.md`
  - `manifest.json`

Requirements

- Write all deliverables in English.
- Keep each platform draft suited to its own publishing context. Do not reuse the same opening line across the pack.
- `x_thread.md` must contain 5 numbered posts.
- `linkedin_post.md` must contain a headline and a single post body.
- `newsletter.md` must include `Subject:` and `Preview:`.
- `short_video_script.md` must contain 6 numbered beats, and every beat must include `Visual:` and `Line:`.
- `manifest.json` must be valid JSON and include one entry for each output file together with the claim ids and source files used for that output.

Notes

- Do not modify the bundled input files under `/app/input/`.
- Do not change the required output paths or filenames.
- Do not modify the tests, validation logic, pinned dependencies, or environment configuration.
- Do not narrow the task to a single draft, a summary only, or a plain list of facts.
- Do not rely on hardcoded copy that only fits one visible snapshot.
- You may add a small local helper script if needed, but the final evaluation will be based on the formal outputs in `/app/output/` and the formal generation entrypoint under `/app/workspace/`.
