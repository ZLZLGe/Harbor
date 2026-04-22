#!/usr/bin/env python3
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from astropy.timeseries import BoxLeastSquares, LombScargle


API_URL = "http://127.0.0.1:8124"
OUTPUT_PATH = Path("/tmp/catalog_vetting_probe.json")


def canonicalize_report(report: dict) -> str:
    import hashlib

    payload = json.dumps(
        report,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_target_frame(target_id: str) -> pd.DataFrame:
    target_root = Path("/app/data/targets") / target_id
    frames = [pd.read_csv(path) for path in sorted(target_root.glob("*.csv"))]
    return pd.concat(frames, ignore_index=True).sort_values("time_mjd").reset_index(drop=True)


def measure_local_depth(flat_flux: np.ndarray, time: np.ndarray, center: float, duration_days: float) -> tuple[float, int]:
    in_event = np.abs(time - center) <= duration_days / 2.0
    near_event = np.abs(time - center) <= duration_days * 2.5
    if int(in_event.sum()) < 3 or int(near_event.sum()) <= int(in_event.sum()):
        return 0.0, int(in_event.sum())
    baseline = float(np.median(flat_flux[near_event & ~in_event]))
    depth = baseline - float(np.median(flat_flux[in_event]))
    return depth, int(in_event.sum())


def analyze_target(target_id: str, manifest: dict) -> tuple[dict, dict]:
    df = load_target_frame(target_id)

    quality_mask = df["quality_flag"].eq(0).to_numpy()
    quarantine_mask = np.zeros(len(df), dtype=bool)
    for lower, upper in manifest["quarantine_windows_mjd"]:
        quarantine_mask |= df["time_mjd"].between(lower, upper).to_numpy()
    used_mask = quality_mask & ~quarantine_mask

    clean = df.loc[used_mask].copy().reset_index(drop=True)
    flux_norm = np.empty(len(clean))
    flux_err_norm = np.empty(len(clean))
    for sector_name in clean["sector"].unique():
        sector_mask = clean["sector"].eq(sector_name).to_numpy()
        sector_median = float(clean.loc[sector_mask, "flux"].median())
        flux_norm[sector_mask] = clean.loc[sector_mask, "flux"].to_numpy() / sector_median
        flux_err_norm[sector_mask] = (
            clean.loc[sector_mask, "flux_err"].to_numpy() / sector_median
        )
    clean["flux_norm"] = flux_norm
    clean["flux_err_norm"] = flux_err_norm

    time = clean["time_mjd"].to_numpy()
    flux = clean["flux_norm"].to_numpy()
    flux_err = clean["flux_err_norm"].to_numpy()

    trend = np.empty_like(flux)
    window = int(manifest["flatten_window_cadences"])
    for sector_name in clean["sector"].unique():
        sector_mask = clean["sector"].eq(sector_name).to_numpy()
        trend[sector_mask] = (
            pd.Series(flux[sector_mask])
            .rolling(window, center=True, min_periods=1)
            .median()
            .to_numpy()
        )
    flat_flux = flux / trend
    flat_flux_err = flux_err / trend

    ls_periods = np.linspace(
        manifest["rotation_scan_days"][0],
        manifest["rotation_scan_days"][1],
        5000,
    )
    ls = LombScargle(time, flux - float(np.mean(flux)))
    ls_power = ls.power(1.0 / ls_periods)
    rotation_alias_days = float(ls_periods[int(np.argmax(ls_power))])

    durations = (
        np.linspace(
            manifest["duration_search_hours"][0],
            manifest["duration_search_hours"][1],
            28,
        )
        / 24.0
    )
    coarse_periods = np.linspace(
        manifest["search_period_days"][0],
        manifest["search_period_days"][1],
        4000,
    )
    bls = BoxLeastSquares(time, flat_flux, flat_flux_err)
    coarse = bls.power(coarse_periods, durations, objective="likelihood")
    coarse_idx = int(np.argmax(coarse.power))
    coarse_period = float(coarse.period[coarse_idx])
    coarse_duration = float(coarse.duration[coarse_idx])

    refine_periods = np.linspace(
        max(manifest["search_period_days"][0], coarse_period * 0.97),
        min(manifest["search_period_days"][1], coarse_period * 1.03),
        5000,
    )
    refine_durations = np.linspace(
        max(durations.min(), coarse_duration - 0.7 / 24.0),
        min(durations.max(), coarse_duration + 0.7 / 24.0),
        81,
    )
    refined = bls.power(refine_periods, refine_durations, objective="likelihood")
    refined_idx = int(np.argmax(refined.power))

    best_period = float(refined.period[refined_idx])
    best_duration = float(refined.duration[refined_idx])
    best_epoch = float(refined.transit_time[refined_idx])
    stats = bls.compute_stats(best_period, best_duration, best_epoch)

    odd_depth, odd_err = stats["depth_odd"]
    even_depth, even_err = stats["depth_even"]
    odd_even_depth_ratio = (
        max(abs(float(odd_depth)), abs(float(even_depth)))
        / max(min(abs(float(odd_depth)), abs(float(even_depth))), 1e-9)
    )
    final_period = best_period
    final_duration = best_duration
    final_epoch = best_epoch
    doubled_period_tested = False

    if odd_even_depth_ratio >= float(manifest["eb_ratio_threshold"]) and best_period * 2.0 <= float(manifest["search_period_days"][1]):
        doubled_period_tested = True
        doubled_center = best_period * 2.0
        doubled_periods = np.linspace(
            max(manifest["search_period_days"][0], doubled_center * 0.97),
            min(manifest["search_period_days"][1], doubled_center * 1.03),
            5000,
        )
        doubled = bls.power(doubled_periods, refine_durations, objective="likelihood")
        doubled_idx = int(np.argmax(doubled.power))
        final_period = float(doubled.period[doubled_idx])
        final_duration = float(doubled.duration[doubled_idx])
        candidate_epoch = float(doubled.transit_time[doubled_idx])
        primary_depth, _ = measure_local_depth(flat_flux, time, candidate_epoch, final_duration)
        secondary_depth, _ = measure_local_depth(
            flat_flux,
            time,
            candidate_epoch + final_period / 2.0,
            final_duration,
        )
        final_epoch = (
            candidate_epoch
            if primary_depth >= secondary_depth
            else candidate_epoch + final_period / 2.0
        )

    final_stats = bls.compute_stats(final_period, final_duration, final_epoch)
    per_transit_counts = np.asarray(final_stats["per_transit_count"])
    cadence_days = float(np.median(np.diff(time)))
    min_points = max(1.0, 0.5 * final_duration / cadence_days)
    transit_count = int(np.sum(per_transit_counts >= min_points))

    in_transit = bls.transit_mask(time, final_period, final_duration, final_epoch)
    baseline_mask = ~in_transit
    baseline_sigma = float(np.std(flat_flux[baseline_mask]))
    primary_depth, primary_points = measure_local_depth(flat_flux, time, final_epoch, final_duration)
    secondary_depth, secondary_points = measure_local_depth(
        flat_flux,
        time,
        final_epoch + final_period / 2.0,
        final_duration,
    )
    transit_snr = (
        primary_depth
        / max(baseline_sigma / np.sqrt(max(primary_points, 1)), 1e-9)
    )
    secondary_eclipse_snr = (
        secondary_depth
        / max(baseline_sigma / np.sqrt(max(secondary_points, 1)), 1e-9)
    )

    verdict = "planet_candidate"
    if (
        odd_even_depth_ratio >= float(manifest["eb_ratio_threshold"])
        or secondary_eclipse_snr >= float(manifest["secondary_eclipse_snr_threshold"])
    ):
        verdict = "eclipsing_binary"

    if verdict == "planet_candidate":
        verdict_reason = (
            "After removing flagged and manifest-quarantined cadences, the cleaned light curve "
            f"still shows a low-frequency activity alias near {rotation_alias_days:.2f} d, "
            f"but the final transit solution at {final_period:.4f} d remains repeatable across "
            f"{transit_count} well-sampled events with no strong odd/even mismatch or secondary eclipse."
        )
    else:
        verdict_reason = (
            f"The strongest dip train resolves to an eclipsing-binary-like solution near {final_period:.4f} d: "
            f"odd/even depth ratio is {odd_even_depth_ratio:.2f} and the secondary-eclipse SNR is "
            f"{secondary_eclipse_snr:.2f}, so this target is not consistent with a clean planet-like transit."
        )

    entry = {
        "target_id": target_id,
        "rotation_alias_days": round(rotation_alias_days, 4),
        "transit_period_days": round(final_period, 5),
        "transit_epoch_mjd": round(final_epoch, 5),
        "duration_hours": round(final_duration * 24.0, 3),
        "depth_ppm": round(primary_depth * 1e6, 1),
        "transit_snr": round(float(transit_snr), 3),
        "transit_count": transit_count,
        "odd_even_depth_ratio": round(float(odd_even_depth_ratio), 3),
        "secondary_eclipse_snr": round(float(secondary_eclipse_snr), 3),
        "quality_points_used": int(used_mask.sum()),
        "quality_points_removed": int((~quality_mask).sum()),
        "quarantine_points_removed": int((quality_mask & quarantine_mask).sum()),
        "verdict": verdict,
        "verdict_reason": verdict_reason,
    }

    diagnostics = {
        "target_id": target_id,
        "initial_period_days": round(best_period, 5),
        "initial_duration_hours": round(best_duration * 24.0, 3),
        "initial_epoch_mjd": round(best_epoch, 5),
        "odd_depth_ppm": round(float(odd_depth) * 1e6, 1),
        "even_depth_ppm": round(float(even_depth) * 1e6, 1),
        "doubled_period_tested": doubled_period_tested,
        "top_rotation_candidates": [
            {
                "period_days": round(float(ls_periods[idx]), 5),
                "power": round(float(ls_power[idx]), 6),
            }
            for idx in np.argsort(ls_power)[-3:][::-1]
        ],
    }
    return entry, diagnostics


def main() -> None:
    catalog = requests.get(f"{API_URL}/catalog", timeout=20).json()
    recommended_entries = []
    diagnostics = []

    for target in catalog["targets"]:
        manifest = requests.get(
            f"{API_URL}/manifest/{target['target_id']}",
            timeout=20,
        ).json()
        entry, diag = analyze_target(target["target_id"], manifest)
        recommended_entries.append(entry)
        diagnostics.append(diag)

    report = {
        "snapshot_id": catalog["snapshot_id"],
        "entries": recommended_entries,
    }
    payload = {
        "snapshot_id": catalog["snapshot_id"],
        "target_count": len(recommended_entries),
        "recommended_entries": recommended_entries,
        "recommended_bundle_sha256": canonicalize_report(report),
        "diagnostics": diagnostics,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"snapshot_id": catalog["snapshot_id"], "target_count": len(recommended_entries)}, indent=2))
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
