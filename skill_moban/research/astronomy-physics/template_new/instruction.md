You are preparing a reproducible follow-up packet for a small candidate set in the NGC 4993 field. The project team has already bundled multi-extension FITS cutouts, rough detector-space seed positions, a split host catalog, a foreground-star slice, and visit metadata into the container, but the formal review deliverables have not been generated yet.

Input data is available in:
- `/root/environment/data/fits/`: field FITS cutouts with science, error, and mask extensions
- `/root/environment/data/detections/`: candidate seed positions, upstream SNR values, and quality flags
- `/root/environment/data/catalogs/`: foreground-star slice plus host coordinate and host property tables
- `/root/environment/data/observations/`: visit metadata, site metadata, calibration values, and screening thresholds
- `/root/environment/pipeline/`: the formal pipeline entrypoint and helper files

Your task:
1. Refine each candidate position by fitting a local point-source model in the bundled FITS science image around the detector-space seed, while keeping the fitted centroid in the FITS 1-indexed pixel convention for every downstream coordinate product.
2. Normalize the observation timestamps from the mixed-format visit metadata to visit midpoints in UTC, then derive the barycentric timing products required by the packet.
3. Combine the bundled host coordinate table with the host property table, cross-match every candidate against the Gaia slice and host catalog, and assign the final screening label and priority rank from the bundled review rules.
4. Compute the calibrated photometric quantities, altitude/airmass context, host-distance context, projected host offsets, and screening diagnostics required by the packet, using the refined centroid and excluding masked pixels from both the source aperture and the background annulus.
5. Make sure the formal entrypoint `python /root/environment/pipeline/build_followup_packet.py --data /root/environment/data --output /root/answer` regenerates all required deliverables.

Output:
- `/root/answer/candidate_followup_packet.ecsv`
  - one row per input candidate
  - required columns:
    `field_id`, `candidate_id`, `fits_file`, `visit_id`, `filter`, `x_seed`, `y_seed`, `x_pixel`, `y_pixel`, `ra_deg`, `dec_deg`, `gal_l_deg`, `gal_b_deg`, `obs_time_iso`, `obs_time_mjd`, `obs_time_bjd_tdb`, `snr`, `quality_flags`, `screening_label`, `priority_rank`
  - `screening_label` must be one of:
    `high_priority_host_associated`, `medium_priority_host_associated`, `reject_foreground_star`, `reject_low_snr`, `reject_bad_measurement`, `review_uncertain_photometry`, `review_large_host_offset`, `review_no_host_match`
- `/root/answer/photometry_context.tsv`
  - one row per input candidate
  - required columns:
    `candidate_id`, `flux_aperture`, `flux_err`, `zeropoint_ab`, `extinction_mag`, `exposure_seconds`, `calibrated_mag`, `mag_unc`, `altitude_deg`, `airmass`, `host_id`, `host_redshift`, `luminosity_distance_mpc`, `projected_offset_kpc`
- `/root/answer/host_association_audit.tsv`
  - one row per input candidate
  - required columns:
    `candidate_id`, `nearest_gaia_id`, `gaia_reference_epoch_jyear`, `gaia_sep_arcsec`, `nearest_host_id`, `host_sep_arcsec`, `host_match_status`, `review_reason`
- `/root/answer/screening_diagnostics.tsv`
  - one row per input candidate
  - required columns:
    `candidate_id`, `seed_offset_pix`, `wcs_roundtrip_x_pixel`, `wcs_roundtrip_y_pixel`, `barycentric_correction_sec`, `gaia_epoch_shift_arcsec`, `gaia_reject_margin_arcsec`, `host_match_margin_arcsec`, `screening_score`
  - margin sign convention:
    `gaia_reject_margin_arcsec` is positive when the candidate lies outside the Gaia reject radius;
    `host_match_margin_arcsec` is positive when the candidate lies inside the host-match radius
- `/root/answer/briefing.json`
  - top-level keys must include:
    `field_id`, `n_input_candidates`, `n_high_priority`, `coordinate_frame`, `time_scale`, `distance_model`, `screening_summary`, `high_priority_candidates`, `notes`
  - each item in `high_priority_candidates` must include:
    `candidate_id`, `ra_deg`, `dec_deg`, `obs_time_iso`, `obs_time_bjd_tdb`, `calibrated_mag`, `screening_label`

Notes:
- Use the bundled inputs to generate the final deliverables. Do not hard-code candidate coordinates, match identities, labels, counts, or summary values.
- Candidate detector seeds are stored in the FITS 1-indexed pixel convention. Keep that convention consistent for both sky reconstruction and the round-trip diagnostic values.
- Treat the detector seeds as coarse starting points. Build the packet from the fitted centroid returned by the local point-source model.
- Use the science, error, and mask extensions named in `/root/environment/data/observations/review_rules.json` as the authoritative image products for refinement and photometry.
- Report observation timestamps at the visit midpoint, not at the visit start.
- `obs_time_bjd_tdb` and `barycentric_correction_sec` must be derived from the visit midpoint, the bundled site metadata, and each candidate sky position.
- `flux_aperture` values are visit-integrated source counts measured from the FITS science image at the refined centroid with the bundled DQ mask respected in both source and background regions. Derive calibrated magnitudes from the count rate implied by `flux_aperture / exposure_seconds`, then apply `zeropoint_ab` and `extinction_mag`.
- Respect the bundled screening thresholds, precedence, and `screening_score` coefficient model from `/root/environment/data/observations/review_rules.json`.
- Combine the bundled host coordinate table with the bundled host property table before host matching.
- Use the bundled foreground-star astrometric fields consistently with the visit midpoint when computing Gaia match separations and Gaia-based screening margins.
- Use the bundled `distance_model` definition from `/root/environment/data/observations/review_rules.json` as the authoritative model description for both `briefing.json` and the host-distance fields in the support tables.
- `briefing.json["screening_summary"]` must be a dictionary keyed by the emitted `screening_label` values, with integer candidate counts.
- Keep the tabular outputs and `briefing.json` mutually consistent.
- Do not modify the input data, tests, dependency setup, or task metadata.
- Do not skip position refinement, time normalization, host-catalog assembly, catalog matching, photometric calibration, host-distance calculations, projected-offset calculations, or report generation.
- The formal entrypoint must write the final outputs to `/root/answer`.
