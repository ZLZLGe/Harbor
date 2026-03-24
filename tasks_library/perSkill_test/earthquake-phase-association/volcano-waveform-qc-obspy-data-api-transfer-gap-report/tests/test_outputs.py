import csv
import json
from pathlib import Path

from obspy import read


OUTPUT_PATH = Path("/root/volcano_trace_qc.json")
MANIFEST_PATH = Path("/root/data/segment_manifest.csv")
SEGMENTS_DIR = Path("/root/data/segments")
ARCHIVE_ID = "volcano-monitoring-qc"


def round6(value):
    return round(float(value), 6)


def format_time(value):
    return value.datetime.strftime("%Y-%m-%dT%H:%M:%S.%f")


def exclusive_end(trace):
    return trace.stats.endtime + trace.stats.delta


def build_expected_report():
    with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        manifest_rows = list(csv.DictReader(handle))

    segments_by_trace = {}
    for row in manifest_rows:
        file_name = row["file_name"]
        stream = read(str(SEGMENTS_DIR / file_name))
        for segment_index, trace in enumerate(stream):
            segments_by_trace.setdefault(trace.id, []).append(
                {
                    "file_name": file_name,
                    "segment_index": segment_index,
                    "trace": trace,
                }
            )

    traces = []
    for trace_id in sorted(segments_by_trace):
        segments = sorted(
            segments_by_trace[trace_id],
            key=lambda item: (
                item["trace"].stats.starttime,
                item["file_name"],
                item["segment_index"],
            ),
        )

        gaps = []
        overlaps = []
        for current, nxt in zip(segments, segments[1:]):
            boundary = exclusive_end(current["trace"])
            diff = nxt["trace"].stats.starttime - boundary
            if diff > 0:
                gaps.append(round6(diff))
            elif diff < 0:
                overlaps.append(round6(-diff))

        start_time = segments[0]["trace"].stats.starttime
        end_time = exclusive_end(segments[-1]["trace"])
        sample_rates = sorted(
            {
                round6(segment["trace"].stats.sampling_rate)
                for segment in segments
            }
        )
        total_gap = round6(sum(gaps))
        total_overlap = round6(sum(overlaps))
        span = round6(end_time - start_time)

        traces.append(
            {
                "trace_id": trace_id,
                "segment_count": len(segments),
                "segment_files": [segment["file_name"] for segment in segments],
                "start_time": format_time(start_time),
                "end_time": format_time(end_time),
                "span_seconds": span,
                "covered_seconds": round6(span - total_gap),
                "sample_rates_hz": sample_rates,
                "sample_rate_inconsistent": len(sample_rates) > 1,
                "gap_count": len(gaps),
                "gap_durations_seconds": gaps,
                "total_gap_seconds": total_gap,
                "overlap_count": len(overlaps),
                "overlap_durations_seconds": overlaps,
                "total_overlap_seconds": total_overlap,
            }
        )

    summary = {
        "trace_count": len(traces),
        "total_segment_count": sum(item["segment_count"] for item in traces),
        "archive_start": min(item["start_time"] for item in traces),
        "archive_end": max(item["end_time"] for item in traces),
        "traces_with_gaps": sum(item["gap_count"] > 0 for item in traces),
        "traces_with_overlaps": sum(item["overlap_count"] > 0 for item in traces),
        "traces_with_sample_rate_inconsistency": sum(
            item["sample_rate_inconsistent"] for item in traces
        ),
        "total_gap_seconds": round6(sum(item["total_gap_seconds"] for item in traces)),
        "total_overlap_seconds": round6(
            sum(item["total_overlap_seconds"] for item in traces)
        ),
    }

    return {
        "archive_id": ARCHIVE_ID,
        "summary": summary,
        "traces": traces,
    }


def test_report_matches_reference():
    actual = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    expected = build_expected_report()

    assert actual == expected
