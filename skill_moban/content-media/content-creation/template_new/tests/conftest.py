from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


TASK_ROOT = Path("/app")
INPUT_ROOT = Path(os.environ.get("TASK_INPUT_ROOT", "/app/input"))
WORKSPACE_ROOT = Path(os.environ.get("TASK_WORKSPACE_ROOT", "/app/workspace"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/app/output"))
BUILD_ENTRYPOINT = WORKSPACE_ROOT / "build_content_pack.py"
BRIEF_PATH = INPUT_ROOT / "brief" / "project_brief.md"
SOURCE_PACKET_PATH = INPUT_ROOT / "brief" / "source_packet.md"
CLAIM_CATALOG_PATH = INPUT_ROOT / "data" / "claim_catalog.json"
SKILL_ROOT = Path(os.environ.get("TASK_SKILL_ROOT", "/root/.codex/skills/content-engine"))
BASELINE_ROOT = Path(os.environ.get("TASK_BASELINE_ROOT", "/opt/task-baselines"))

COUNTRY_ORDER = ["CAN", "MEX", "USA"]
COUNTRY_NAMES = {"CAN": "Canada", "MEX": "Mexico", "USA": "United States"}
SOURCE_LABELS = ["Other renewables", "Bioenergy", "Solar", "Wind", "Hydropower", "Nuclear", "Oil", "Gas", "Coal"]
CLEAN_SOURCES = ["Other renewables", "Bioenergy", "Solar", "Wind", "Hydropower", "Nuclear"]
OUTPUT_FILES = [
    "core_angle.md",
    "x_thread.md",
    "linkedin_post.md",
    "newsletter.md",
    "short_video_script.md",
    "manifest.json",
]


def run_pack(input_root: Path = INPUT_ROOT, output_root: Path = OUTPUT_ROOT) -> subprocess.CompletedProcess[str]:
    output_root.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [
            "python3",
            str(BUILD_ENTRYPOINT),
            "--input-root",
            str(input_root),
            "--output-root",
            str(output_root),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def normalize_space(text: str) -> str:
    return " ".join(text.split())


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_brief(path: Path = BRIEF_PATH) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not match:
        raise AssertionError("project_brief.md is missing its JSON contract block")
    return json.loads(match.group(1))


def latest_common_world_bank_year(rows: list[dict], codes: list[str]) -> tuple[int, dict[str, float]]:
    filtered = [row for row in rows if row["countryiso3code"] in codes and row["value"] is not None]
    years = sorted({int(row["date"]) for row in filtered}, reverse=True)
    for year in years:
        sample = {row["countryiso3code"]: float(row["value"]) for row in filtered if int(row["date"]) == year}
        if set(sample) == set(codes):
            return year, sample
    raise AssertionError("missing common World Bank year")


def latest_common_csv_year(rows: list[dict[str, str]], codes: list[str], value_columns: list[str]) -> tuple[int, dict[str, dict[str, float]]]:
    years = sorted({int(row["Year"]) for row in rows if row["Code"] in codes}, reverse=True)
    for year in years:
        sample: dict[str, dict[str, float]] = {}
        for row in rows:
            if row["Code"] not in codes or int(row["Year"]) != year:
                continue
            values: dict[str, float] = {}
            for column in value_columns:
                raw = row.get(column, "")
                if raw in ("", None):
                    continue
                values[column] = float(raw)
            if values:
                sample[row["Code"]] = values
        if set(sample) == set(codes):
            return year, sample
    raise AssertionError("missing common CSV year")


def fmt_millions(value: float) -> str:
    return f"{value / 1_000_000:.1f}M"


def fmt_trillions(value: float) -> str:
    return f"${value / 1_000_000_000_000:.2f}T"


def fmt_megatonnes(value: float) -> str:
    return f"{value / 1_000_000:.1f} Mt"


def fmt_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def fmt_twh(value: float) -> str:
    return f"{value:,.1f} TWh"


def total_generation(values: dict[str, float]) -> float:
    return sum(values.get(source, 0.0) for source in SOURCE_LABELS)


def clean_total(values: dict[str, float]) -> float:
    return sum(values.get(source, 0.0) for source in CLEAN_SOURCES)


def build_claim_catalog(input_root: Path = INPUT_ROOT) -> dict:
    pop_year, pop_values = latest_common_world_bank_year(load_json(input_root / "data" / "world_bank_population.json")[1], COUNTRY_ORDER)
    gdp_year, gdp_values = latest_common_world_bank_year(load_json(input_root / "data" / "world_bank_gdp.json")[1], COUNTRY_ORDER)

    co2_rows = load_csv_rows(input_root / "data" / "annual_co2_emissions.csv")
    co2_column = "Annual CO₂ emissions" if "Annual CO₂ emissions" in co2_rows[0] else "Annual CO2 emissions"
    co2_year, co2_values_raw = latest_common_csv_year(co2_rows, COUNTRY_ORDER, [co2_column])
    co2_values = {code: payload[co2_column] for code, payload in co2_values_raw.items()}

    electricity_rows = load_csv_rows(input_root / "data" / "electricity_prod_source.csv")
    electricity_year, electricity_values = latest_common_csv_year(electricity_rows, COUNTRY_ORDER, SOURCE_LABELS)

    clean_share = {code: clean_total(values) / total_generation(values) for code, values in electricity_values.items()}
    gas_share = {code: electricity_values[code]["Gas"] / total_generation(electricity_values[code]) for code in COUNTRY_ORDER}

    claims = [
        {
            "id": "C01_US_POPULATION_SCALE",
            "headline": "The United States remained the region's population heavyweight.",
            "statement": f"In {pop_year}, the United States had {fmt_millions(pop_values['USA'])} people, compared with {fmt_millions(pop_values['MEX'])} in Mexico and {fmt_millions(pop_values['CAN'])} in Canada.",
            "country": "United States",
            "year": pop_year,
            "metric_value": fmt_millions(pop_values["USA"]),
            "verification_tokens": ["United States", fmt_millions(pop_values["USA"]), str(pop_year)],
            "source_files": ["data/world_bank_population.json"],
            "why_it_matters": "Scale explains why the United States can dominate regional totals even when a share-based comparison points elsewhere.",
            "visual": "Population bars for Canada, Mexico, and the United States.",
        },
        {
            "id": "C02_US_GDP_SCALE",
            "headline": "The United States operated at a much larger GDP scale than its neighbors.",
            "statement": f"In {gdp_year}, the United States posted a GDP of {fmt_trillions(gdp_values['USA'])}, versus {fmt_trillions(gdp_values['CAN'])} for Canada and {fmt_trillions(gdp_values['MEX'])} for Mexico.",
            "country": "United States",
            "year": gdp_year,
            "metric_value": fmt_trillions(gdp_values["USA"]),
            "verification_tokens": ["United States", fmt_trillions(gdp_values["USA"]), str(gdp_year)],
            "source_files": ["data/world_bank_gdp.json"],
            "why_it_matters": "Business readers need the scale context before they interpret generation totals or policy choices.",
            "visual": "GDP comparison bars with all three countries on one axis.",
        },
        {
            "id": "C03_CANADA_CLEAN_SHARE",
            "headline": "Canada was the clean-share outlier in the latest power mix.",
            "statement": f"In {electricity_year}, clean sources supplied {fmt_percent(clean_share['CAN'])} of Canada's electricity mix, ahead of the United States at {fmt_percent(clean_share['USA'])} and Mexico at {fmt_percent(clean_share['MEX'])}.",
            "country": "Canada",
            "year": electricity_year,
            "metric_value": fmt_percent(clean_share["CAN"]),
            "verification_tokens": ["Canada", fmt_percent(clean_share["CAN"]), str(electricity_year)],
            "source_files": ["data/electricity_prod_source.csv"],
            "why_it_matters": "This is the clearest opening contrast for the package because it names the regional outlier and frames the rest of the comparison.",
            "visual": "Clean-share bars for Canada, Mexico, and the United States.",
        },
        {
            "id": "C04_CANADA_HYDRO_LEAD",
            "headline": "Hydropower remained Canada's largest single source.",
            "statement": f"Hydropower led Canada's {electricity_year} generation stack at {fmt_twh(electricity_values['CAN']['Hydropower'])}, well ahead of gas and wind.",
            "country": "Canada",
            "year": electricity_year,
            "metric_value": fmt_twh(electricity_values["CAN"]["Hydropower"]),
            "verification_tokens": ["Hydropower", "Canada", f"{electricity_values['CAN']['Hydropower']:.1f}", str(electricity_year)],
            "source_files": ["data/electricity_prod_source.csv"],
            "why_it_matters": "The Canada angle is stronger when the clean-share lead is grounded in the source that anchors the stack.",
            "visual": "Canada source stack with hydropower highlighted.",
        },
        {
            "id": "C05_MEXICO_GAS_RELIANCE",
            "headline": "Mexico remained the gas-heavy outlier in the latest mix.",
            "statement": f"Gas supplied {fmt_percent(gas_share['MEX'])} of Mexico's electricity mix in {electricity_year}, the highest gas share of the three markets.",
            "country": "Mexico",
            "year": electricity_year,
            "metric_value": fmt_percent(gas_share["MEX"]),
            "verification_tokens": ["Mexico", fmt_percent(gas_share["MEX"]), "gas", str(electricity_year)],
            "source_files": ["data/electricity_prod_source.csv"],
            "why_it_matters": "This gives the package a clear counterpoint to Canada's cleaner grid profile.",
            "visual": "Mexico generation stack with gas highlighted.",
        },
        {
            "id": "C06_MEXICO_LOWEST_CO2",
            "headline": "Mexico posted the lowest annual CO2 total in the latest year.",
            "statement": f"In {co2_year}, Mexico recorded {fmt_megatonnes(co2_values['MEX'])} of annual CO2 emissions, below Canada's {fmt_megatonnes(co2_values['CAN'])} and far below the United States at {fmt_megatonnes(co2_values['USA'])}.",
            "country": "Mexico",
            "year": co2_year,
            "metric_value": fmt_megatonnes(co2_values["MEX"]),
            "verification_tokens": ["Mexico", fmt_megatonnes(co2_values["MEX"]), str(co2_year)],
            "source_files": ["data/annual_co2_emissions.csv"],
            "why_it_matters": "The emissions comparison keeps the package from collapsing into a power-mix story only.",
            "visual": "Latest annual CO2 totals for the three countries.",
        },
        {
            "id": "C07_US_CLEAN_SCALE",
            "headline": "The United States still led the region on clean-power volume.",
            "statement": f"The United States generated {fmt_twh(clean_total(electricity_values['USA']))} from clean sources in {electricity_year}, the largest absolute clean-power total in this three-country set.",
            "country": "United States",
            "year": electricity_year,
            "metric_value": fmt_twh(clean_total(electricity_values["USA"])),
            "verification_tokens": ["United States", f"{clean_total(electricity_values['USA']):,.1f}", "clean", str(electricity_year)],
            "source_files": ["data/electricity_prod_source.csv"],
            "why_it_matters": "The U.S. line keeps the package honest: the clean-share lag does not erase the scale of clean generation already on the system.",
            "visual": "Absolute clean-generation totals for the three countries.",
        },
    ]

    return {
        "metric_years": {
            "population_year": pop_year,
            "gdp_year": gdp_year,
            "co2_year": co2_year,
            "electricity_year": electricity_year,
        },
        "countries": [COUNTRY_NAMES[code] for code in COUNTRY_ORDER],
        "claims": claims,
    }


def render_source_packet(catalog: dict) -> str:
    claims = {entry["id"]: entry for entry in catalog["claims"]}
    return (
        "# Source Packet\n\n"
        "## One-line read\n\n"
        "North America's latest power picture splits three ways: Canada is the clean-share outlier, Mexico remains the gas-heavy counterpoint, and the United States still moves at unmatched clean-power scale.\n\n"
        "## Snapshot years\n\n"
        f"- Population series: {catalog['metric_years']['population_year']}\n"
        f"- GDP series: {catalog['metric_years']['gdp_year']}\n"
        f"- Annual CO2 series: {catalog['metric_years']['co2_year']}\n"
        f"- Electricity mix series: {catalog['metric_years']['electricity_year']}\n\n"
        "## Publishable facts\n\n"
        f"- C03_CANADA_CLEAN_SHARE: {claims['C03_CANADA_CLEAN_SHARE']['statement']}\n"
        f"- C04_CANADA_HYDRO_LEAD: {claims['C04_CANADA_HYDRO_LEAD']['statement']}\n"
        f"- C05_MEXICO_GAS_RELIANCE: {claims['C05_MEXICO_GAS_RELIANCE']['statement']}\n"
        f"- C06_MEXICO_LOWEST_CO2: {claims['C06_MEXICO_LOWEST_CO2']['statement']}\n"
        f"- C07_US_CLEAN_SCALE: {claims['C07_US_CLEAN_SCALE']['statement']}\n"
        f"- C02_US_GDP_SCALE: {claims['C02_US_GDP_SCALE']['statement']}\n"
        f"- C01_US_POPULATION_SCALE: {claims['C01_US_POPULATION_SCALE']['statement']}\n\n"
        "## Editorial angle\n\n"
        "Lead with the clean-share gap first, then pivot to the gas-heavy Mexico line, and close the main comparison with the scale of U.S. clean generation. The GDP and population points are useful for background and newsletter framing.\n\n"
        "## Watchouts\n\n"
        "- Keep the share claims separate from the absolute-volume claims.\n"
        "- Keep the latest-year labels attached to every key number.\n"
        "- Use the emissions line as a contrast point, not as a full causal claim.\n"
        "- Keep the closing CTA practical and light.\n"
    )


def expected_context(input_root: Path = INPUT_ROOT) -> dict:
    return {
        "brief": parse_brief(input_root / "brief" / "project_brief.md"),
        "expected_catalog": build_claim_catalog(input_root),
        "shipped_catalog": load_json(input_root / "data" / "claim_catalog.json"),
    }


def claim_map(catalog: dict) -> dict[str, dict]:
    return {claim["id"]: claim for claim in catalog["claims"]}


def manifest_entry(manifest: dict, filename: str) -> dict:
    for entry in manifest["outputs"]:
        entry_name = entry.get("file") or entry.get("output_file")
        if entry_name == filename:
            return entry
    raise AssertionError(f"Missing manifest entry for {filename}")


def token_variants(token: str) -> set[str]:
    variants = {token.lower()}
    if "," in token:
        variants.add(token.replace(",", "").lower())
    if token.endswith(" Mt"):
        variants.add(token.replace(" Mt", "mt").lower())
    return variants


def assert_claim_tokens_present(text: str, claims: list[dict]) -> None:
    haystack = normalize_space(text).lower()
    for claim in claims:
        for token in claim["verification_tokens"]:
            assert any(variant in haystack for variant in token_variants(token)), f"Missing token {token} for {claim['id']}"


def numbered_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if re.match(r"^\d+\.(?:\s|$)", line):
            if current:
                blocks.append("\n".join(current).strip())
            current = [line]
            continue
        if current:
            current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return blocks


def first_meaningful_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        return stripped
    return ""


def current_hash_lines(root: Path) -> str:
    if not root.exists():
        return ""
    return subprocess.check_output(
        f"cd {root} && find . -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )


def make_alternate_input_copy() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    tmpdir = tempfile.TemporaryDirectory()
    alt_root = Path(tmpdir.name) / "input"
    shutil.copytree(INPUT_ROOT, alt_root)

    gdp_payload = load_json(alt_root / "data" / "world_bank_gdp.json")
    for row in gdp_payload[1]:
        if row["date"] == "2024" and row["countryiso3code"] == "USA" and row["value"] is not None:
            row["value"] = 25098000000000.0
    (alt_root / "data" / "world_bank_gdp.json").write_text(json.dumps(gdp_payload), encoding="utf-8")

    electricity_rows = load_csv_rows(alt_root / "data" / "electricity_prod_source.csv")
    for row in electricity_rows:
        if row["Code"] == "CAN" and row["Year"] == "2025":
            row["Gas"] = "60.0"
            row["Wind"] = "150.0"
            row["Hydropower"] = "352.0"
        if row["Code"] == "MEX" and row["Year"] == "2025":
            row["Gas"] = "185.0"
            row["Solar"] = "42.0"
            row["Wind"] = "31.0"
        if row["Code"] == "USA" and row["Year"] == "2025":
            row["Gas"] = "1685.0"
            row["Solar"] = "480.0"
            row["Wind"] = "560.0"
    with (alt_root / "data" / "electricity_prod_source.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=electricity_rows[0].keys())
        writer.writeheader()
        writer.writerows(electricity_rows)

    co2_rows = load_csv_rows(alt_root / "data" / "annual_co2_emissions.csv")
    co2_column = "Annual CO₂ emissions" if "Annual CO₂ emissions" in co2_rows[0] else "Annual CO2 emissions"
    for row in co2_rows:
        if row["Code"] == "MEX" and row["Year"] == "2024":
            row[co2_column] = "398000000.0"
    with (alt_root / "data" / "annual_co2_emissions.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=co2_rows[0].keys())
        writer.writeheader()
        writer.writerows(co2_rows)

    updated_catalog = build_claim_catalog(alt_root)
    (alt_root / "data" / "claim_catalog.json").write_text(json.dumps(updated_catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (alt_root / "brief" / "source_packet.md").write_text(render_source_packet(updated_catalog), encoding="utf-8")
    return tmpdir, alt_root
