You are preparing a reproducible follow-up packet for a small candidate set in the NGC 4993 field. The project team has already bundled public field cutouts, detector-space candidate picks, a foreground-star reference slice, a host-galaxy reference table, and observation metadata into the container, but the formal review deliverables have not been generated yet.

Input data is available in:
- `/root/environment/data/fits/`: field FITS cutouts with WCS headers
- `/root/environment/data/detections/`: candidate pixel locations, fluxes, flux errors, SNR values, and quality flags
- `/root/environment/data/catalogs/`: foreground-star and host-galaxy reference data
- `/root/environment/data/observations/`: visit metadata, calibration values, and screening thresholds
- `/root/environment/pipeline/`: the formal pipeline entrypoint and helper files

Your task:
1. Rebuild each candidate in sky coordinates from the bundled FITS inputs and detector-space detections, then normalize the observation times required by the packet.
2. Cross-match every candidate against the bundled foreground-star slice and host catalog, then assign the final screening label and priority rank from the bundled review rules.
3. Compute the calibrated photometric quantities, host-distance context, projected host offsets, and screening diagnostics required by the packet, keeping the scientific conventions internally consistent across all outputs.
4. Generate a complete audit trail so every candidate can be traced from detector-space inputs to final screening label, nearest matches, and review metrics.
5. Make sure the formal entrypoint `python /root/environment/pipeline/build_followup_packet.py --data /root/environment/data --output /root/answer` regenerates all required deliverables.

Output:
- `/root/answer/candidate_followup_packet.ecsv`
  - one row per input candidate
  - required columns:
    `field_id`, `candidate_id`, `fits_file`, `visit_id`, `filter`, `x_pixel`, `y_pixel`, `ra_deg`, `dec_deg`, `gal_l_deg`, `gal_b_deg`, `obs_time_iso`, `obs_time_mjd`, `snr`, `quality_flags`, `screening_label`, `priority_rank`
  - `screening_label` must be one of:
    `high_priority_host_associated`, `medium_priority_host_associated`, `reject_foreground_star`, `reject_low_snr`, `reject_bad_measurement`, `review_uncertain_photometry`, `review_large_host_offset`, `review_no_host_match`
- `/root/answer/photometry_context.tsv`
  - one row per input candidate
  - required columns:
    `candidate_id`, `flux_aperture`, `flux_err`, `zeropoint_ab`, `extinction_mag`, `exposure_seconds`, `calibrated_mag`, `mag_unc`, `host_id`, `host_redshift`, `luminosity_distance_mpc`, `projected_offset_kpc`
- `/root/answer/host_association_audit.tsv`
  - one row per input candidate
  - required columns:
    `candidate_id`, `nearest_gaia_id`, `gaia_sep_arcsec`, `nearest_host_id`, `host_sep_arcsec`, `host_match_status`, `review_reason`
- `/root/answer/screening_diagnostics.tsv`
  - one row per input candidate
  - required columns:
    `candidate_id`, `wcs_roundtrip_x_pixel`, `wcs_roundtrip_y_pixel`, `gaia_reject_margin_arcsec`, `host_match_margin_arcsec`, `screening_score`
- `/root/answer/briefing.json`
  - top-level keys must include:
    `field_id`, `n_input_candidates`, `n_high_priority`, `coordinate_frame`, `time_scale`, `distance_model`, `screening_summary`, `high_priority_candidates`, `notes`
  - each item in `high_priority_candidates` must include:
    `candidate_id`, `ra_deg`, `dec_deg`, `obs_time_iso`, `calibrated_mag`, `screening_label`

Notes:
- Use the bundled inputs to generate the final deliverables. Do not hard-code candidate coordinates, match identities, labels, counts, or summary values.
- Respect the bundled screening thresholds and precedence from `/root/environment/data/observations/review_rules.json`.
- Use the bundled `distance_model` definition from `/root/environment/data/observations/review_rules.json` as the authoritative model description for both `briefing.json` and the host-distance fields in the support tables.
- `briefing.json["screening_summary"]` must be a dictionary keyed by the emitted `screening_label` values, with integer candidate counts.
- Keep the tabular outputs and `briefing.json` mutually consistent.
- Do not modify the input data, tests, dependency setup, or task metadata.
- Do not skip position reconstruction, time normalization, catalog matching, photometric calibration, host-distance calculations, projected-offset calculations, or report generation.
- The formal entrypoint must write the final outputs to `/root/answer`.
