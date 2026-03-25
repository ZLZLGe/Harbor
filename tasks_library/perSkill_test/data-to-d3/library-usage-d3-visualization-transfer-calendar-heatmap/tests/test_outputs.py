import calendar
import csv
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

INPUT_CSV = Path("/root/data/library_daily_checkouts_2025.csv")
OUTPUT_SVG = Path("/root/output/library-checkout-heatmap.svg")
SVG_NS = {"svg": "http://www.w3.org/2000/svg"}


def parse_rows():
    with INPUT_CSV.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    parsed = []
    for row in rows:
        parsed.append(
            {
                "date": row["date"],
                "checkout_count": int(row["checkout_count"]),
                "holiday_name": row["holiday_name"],
                "event_label": row["event_label"],
            }
        )
    return parsed


def month_key(date_string):
    return date_string[:7]


def weekday_index(date_string):
    date_value = datetime.strptime(date_string, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return date_value.weekday()


def week_index(date_string):
    date_value = datetime.strptime(date_string, "%Y-%m-%d").date()
    month_start = date_value.replace(day=1)
    return (date_value.day + month_start.weekday() - 1) // 7


def has_class(element, class_name):
    classes = element.attrib.get("class", "").split()
    return class_name in classes


def text_content(element):
    return "".join(element.itertext()).strip()


EXPECTED_ROWS = parse_rows()
EXPECTED_BY_DATE = {row["date"]: row for row in EXPECTED_ROWS}
EXPECTED_MONTHS = sorted({month_key(row["date"]) for row in EXPECTED_ROWS})
HOLIDAY_DATES = sorted(row["date"] for row in EXPECTED_ROWS if row["holiday_name"])
PEAK_ROWS = sorted(
    EXPECTED_ROWS,
    key=lambda row: (-row["checkout_count"], row["date"]),
)[:3]


@pytest.fixture(scope="module")
def svg_root():
    if not OUTPUT_SVG.exists():
        pytest.fail(f"Missing output SVG: {OUTPUT_SVG}")

    tree = ET.parse(OUTPUT_SVG)
    root = tree.getroot()
    return root


def iter_elements(root, tag_name):
    return root.findall(f".//svg:{tag_name}", SVG_NS)


def find_by_id(root, element_id):
    for element in root.iter():
        if element.attrib.get("id") == element_id:
            return element
    return None


def test_svg_file_exists_and_is_standalone(svg_root):
    assert OUTPUT_SVG.is_file(), f"Expected SVG output at {OUTPUT_SVG}"
    assert svg_root.tag.endswith("svg"), "Root element must be <svg>"
    assert svg_root.attrib.get("id") == "library-checkout-report", "Root SVG id must be library-checkout-report"

    raw_svg = OUTPUT_SVG.read_text(encoding="utf-8")
    assert "<script" not in raw_svg.lower(), "Standalone SVG must not contain <script> tags"
    assert "<html" not in raw_svg.lower(), "Output must be raw SVG, not HTML"


def test_month_panels_and_day_cells_match_csv(svg_root):
    panels = [element for element in iter_elements(svg_root, "g") if has_class(element, "month-panel")]
    assert len(panels) == 12, f"Expected 12 month panels, found {len(panels)}"

    panel_by_month = {panel.attrib.get("data-month"): panel for panel in panels}
    assert sorted(panel_by_month) == EXPECTED_MONTHS, f"Month panel keys do not match expected months: {sorted(panel_by_month)}"

    day_cells = [element for element in iter_elements(svg_root, "rect") if has_class(element, "day-cell")]
    assert len(day_cells) == len(EXPECTED_ROWS), f"Expected {len(EXPECTED_ROWS)} day cells, found {len(day_cells)}"

    seen_dates = set()
    for panel in panels:
        panel_month = panel.attrib.get("data-month")
        month_label = next((child for child in panel if child.tag.endswith("text") and has_class(child, "month-label")), None)
        assert month_label is not None, f"Month panel {panel_month} is missing a month-label text node"

        panel_cells = [element for element in panel.findall(".//svg:rect", SVG_NS) if has_class(element, "day-cell")]
        expected_days = calendar.monthrange(2025, int(panel_month[-2:]))[1]
        assert len(panel_cells) == expected_days, f"Month {panel_month} should contain {expected_days} day cells, found {len(panel_cells)}"

        for cell in panel_cells:
            date_value = cell.attrib.get("data-date")
            assert date_value in EXPECTED_BY_DATE, f"Unexpected data-date on day cell: {date_value}"
            assert date_value not in seen_dates, f"Duplicate day cell for {date_value}"
            seen_dates.add(date_value)

            expected = EXPECTED_BY_DATE[date_value]
            assert cell.attrib.get("data-count") == str(expected["checkout_count"]), f"data-count mismatch for {date_value}"
            assert cell.attrib.get("data-month") == panel_month == month_key(date_value), f"data-month mismatch for {date_value}"
            assert cell.attrib.get("data-weekday") == str(weekday_index(date_value)), f"data-weekday mismatch for {date_value}"
            assert cell.attrib.get("data-week-index") == str(week_index(date_value)), f"data-week-index mismatch for {date_value}"

            is_weekend = weekday_index(date_value) >= 5
            is_holiday = bool(expected["holiday_name"])
            assert cell.attrib.get("data-weekend") == str(is_weekend).lower(), f"data-weekend mismatch for {date_value}"
            assert cell.attrib.get("data-holiday") == str(is_holiday).lower(), f"data-holiday mismatch for {date_value}"

            if is_weekend:
                assert has_class(cell, "weekend"), f"Weekend cell {date_value} must include weekend class"
            else:
                assert not has_class(cell, "weekend"), f"Weekday cell {date_value} must not include weekend class"

            if is_holiday:
                assert cell.attrib.get("data-holiday-name") == expected["holiday_name"], f"Missing or incorrect data-holiday-name for {date_value}"
            else:
                assert "data-holiday-name" not in cell.attrib, f"Non-holiday cell {date_value} should not include data-holiday-name"

    assert seen_dates == set(EXPECTED_BY_DATE), "The SVG does not contain exactly one day cell for every CSV date"


def test_calendar_grid_alignment_within_each_month(svg_root):
    panels = [element for element in iter_elements(svg_root, "g") if has_class(element, "month-panel")]

    for panel in panels:
        by_weekday = {}
        by_week_index = {}
        for cell in [element for element in panel.findall(".//svg:rect", SVG_NS) if has_class(element, "day-cell")]:
            weekday = cell.attrib["data-weekday"]
            week = cell.attrib["data-week-index"]
            x_value = float(cell.attrib["x"])
            y_value = float(cell.attrib["y"])

            by_weekday.setdefault(weekday, set()).add(x_value)
            by_week_index.setdefault(week, set()).add(y_value)

        for weekday, x_values in by_weekday.items():
            assert len(x_values) == 1, f"Month {panel.attrib['data-month']} weekday {weekday} should stay in one column, got {sorted(x_values)}"
        for week, y_values in by_week_index.items():
            assert len(y_values) == 1, f"Month {panel.attrib['data-month']} week {week} should stay in one row, got {sorted(y_values)}"


def test_color_legend_and_fill_scale(svg_root):
    legend = find_by_id(svg_root, "checkout-legend")
    assert legend is not None, "Missing legend group with id checkout-legend"

    swatches = [element for element in legend.findall(".//svg:rect", SVG_NS) if has_class(element, "legend-swatch")]
    assert len(swatches) == 5, f"Legend must contain exactly 5 legend-swatch rects, found {len(swatches)}"

    swatch_fills = [swatch.attrib.get("fill") for swatch in swatches]
    assert all(swatch_fills), "Every legend swatch must have a fill color"
    assert len(set(swatch_fills)) == 5, f"Legend swatches should use 5 distinct colors, got {swatch_fills}"

    day_cells = [element for element in iter_elements(svg_root, "rect") if has_class(element, "day-cell")]
    unique_day_fills = {cell.attrib.get("fill") for cell in day_cells}
    assert None not in unique_day_fills, "All day cells must declare a fill color"
    assert len(unique_day_fills) >= 5, f"Expected at least 5 distinct fill colors across the heatmap, found {len(unique_day_fills)}"

    min_text = next((element for element in legend.findall(".//svg:text", SVG_NS) if has_class(element, "legend-min")), None)
    max_text = next((element for element in legend.findall(".//svg:text", SVG_NS) if has_class(element, "legend-max")), None)
    assert min_text is not None, "Legend is missing text.legend-min"
    assert max_text is not None, "Legend is missing text.legend-max"

    expected_min = min(row["checkout_count"] for row in EXPECTED_ROWS)
    expected_max = max(row["checkout_count"] for row in EXPECTED_ROWS)
    assert str(expected_min) in text_content(min_text), f"legend-min text must include {expected_min}"
    assert str(expected_max) in text_content(max_text), f"legend-max text must include {expected_max}"


def test_holiday_markers_exist_for_all_holidays(svg_root):
    holiday_markers = [element for element in iter_elements(svg_root, "circle") if has_class(element, "holiday-marker")]
    marker_dates = sorted(marker.attrib.get("data-date") for marker in holiday_markers)
    assert marker_dates == HOLIDAY_DATES, f"Holiday marker dates do not match expected holidays: {marker_dates}"


def test_peak_annotations_cover_top_three_dates(svg_root):
    container = find_by_id(svg_root, "peak-annotations")
    assert container is not None, "Missing annotation container with id peak-annotations"

    annotations = [element for element in container.findall(".//svg:text", SVG_NS) if has_class(element, "peak-annotation")]
    assert len(annotations) == 3, f"Expected exactly 3 peak annotations, found {len(annotations)}"

    annotation_by_date = {annotation.attrib.get("data-date"): annotation for annotation in annotations}
    expected_dates = [row["date"] for row in PEAK_ROWS]
    assert sorted(annotation_by_date) == sorted(expected_dates), f"Peak annotation dates mismatch: {sorted(annotation_by_date)}"

    for row in PEAK_ROWS:
        annotation = annotation_by_date.get(row["date"])
        assert annotation is not None, f"Missing peak annotation for {row['date']}"
        content = text_content(annotation)
        assert row["date"] in content, f"Peak annotation for {row['date']} must include the date"
        assert str(row["checkout_count"]) in content, f"Peak annotation for {row['date']} must include the checkout count"
        if row["event_label"]:
            assert row["event_label"] in content, f"Peak annotation for {row['date']} must include event_label '{row['event_label']}'"
