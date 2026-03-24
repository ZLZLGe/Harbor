import json
import os
import re


APP_DIR = "/app"
MANIFEST_PATH = os.path.join(APP_DIR, "assay_batches.json")
PRIMARY_OUTPUT = os.path.join(APP_DIR, "assay_plans/batch_red_plan.txt")
ACTION_RE = re.compile(r"^([a-z0-9-]+)\(([^)]*)\)$")


def load_manifest():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def app_path(relative_path):
    return os.path.join(APP_DIR, relative_path)


def read_plan_lines(plan_path):
    with open(plan_path, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle.readlines() if line.strip()]


def parse_actions(plan_lines):
    actions = []
    for line in plan_lines:
        match = ACTION_RE.match(line)
        assert match, f"Invalid action syntax: {line}"
        raw_args = [part.strip() for part in match.group(2).split(",") if part.strip()]
        actions.append((match.group(1), raw_args))
    return actions


def load_problem_objects(item):
    object_names = set()
    in_objects = False

    with open(app_path(item["problem"]), "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("(:objects"):
                in_objects = True
                continue
            if in_objects and line.startswith("(:init"):
                break
            if in_objects and " - " in line:
                names_part, _, _ = line.rpartition(" - ")
                cleaned_names = names_part.replace(")", " ")
                object_names.update(token for token in cleaned_names.split() if token)

    return object_names


def simulate_batch(item, actions, object_names):
    wells = item["well_order"]
    samples = item["samples"]
    reagents = item["reagents"]

    assert wells, item["id"]
    assert len(wells) == len(samples) == len(reagents), item["id"]

    well_set = set(wells)
    sample_to_well = dict(zip(samples, wells))
    reagent_to_well = dict(zip(reagents, wells))

    state = {
        "aliquoted": set(),
        "reagent_added": set(),
        "mixed": set(),
        "washed": set(),
        "readout": set(),
        "mix_index": 0,
        "wash_index": 0,
        "read_index": 0,
        "incubated": False,
        "loaded": False,
        "complete": False,
    }
    counts = {
        "aliquot-sample": 0,
        "add-reagent": 0,
        "mix": 0,
        "mix-final": 0,
        "incubate-plate": 0,
        "wash": 0,
        "wash-final": 0,
        "load-reader": 0,
        "read": 0,
        "read-final": 0,
    }

    for name, args in actions:
        unknown = [arg for arg in args if arg not in object_names]
        assert not unknown, f"Unknown objects in {item['id']}: {unknown}"

        if name == "aliquot-sample":
            counts[name] += 1
            assert len(args) == 3, args
            sample, well, plate = args
            assert plate == item["plate"], args
            assert well in well_set, args
            assert sample_to_well.get(sample) == well, args
            assert well not in state["aliquoted"], args
            state["aliquoted"].add(well)
            continue

        if name == "add-reagent":
            counts[name] += 1
            assert len(args) == 3, args
            reagent, well, plate = args
            assert plate == item["plate"], args
            assert well in well_set, args
            assert reagent_to_well.get(reagent) == well, args
            assert well in state["aliquoted"], args
            assert well not in state["reagent_added"], args
            state["reagent_added"].add(well)
            continue

        if name == "mix-well":
            counts["mix"] += 1
            assert len(args) == 3, args
            well, next_well, plate = args
            assert plate == item["plate"], args
            assert state["mix_index"] < len(wells) - 1, args
            assert well == wells[state["mix_index"]], args
            assert next_well == wells[state["mix_index"] + 1], args
            assert well in state["aliquoted"], args
            assert well in state["reagent_added"], args
            assert well not in state["mixed"], args
            state["mixed"].add(well)
            state["mix_index"] += 1
            continue

        if name == "mix-final-well":
            counts["mix-final"] += 1
            assert len(args) == 2, args
            well, plate = args
            assert plate == item["plate"], args
            assert state["mix_index"] == len(wells) - 1, args
            assert well == wells[state["mix_index"]], args
            assert well in state["aliquoted"], args
            assert well in state["reagent_added"], args
            assert well not in state["mixed"], args
            state["mixed"].add(well)
            state["mix_index"] += 1
            continue

        if name == "incubate-plate":
            counts[name] += 1
            assert len(args) == 2, args
            plate, incubator = args
            assert plate == item["plate"], args
            assert incubator == item["incubator"], args
            assert len(state["mixed"]) == len(wells), args
            assert not state["incubated"], args
            state["incubated"] = True
            continue

        if name == "wash-well":
            counts["wash"] += 1
            assert len(args) == 4, args
            well, next_well, plate, washer = args
            assert plate == item["plate"], args
            assert washer == item["washer"], args
            assert state["incubated"], args
            assert state["wash_index"] < len(wells) - 1, args
            assert well == wells[state["wash_index"]], args
            assert next_well == wells[state["wash_index"] + 1], args
            assert well in state["mixed"], args
            assert well not in state["washed"], args
            state["washed"].add(well)
            state["wash_index"] += 1
            continue

        if name == "wash-final-well":
            counts["wash-final"] += 1
            assert len(args) == 3, args
            well, plate, washer = args
            assert plate == item["plate"], args
            assert washer == item["washer"], args
            assert state["incubated"], args
            assert state["wash_index"] == len(wells) - 1, args
            assert well == wells[state["wash_index"]], args
            assert well in state["mixed"], args
            assert well not in state["washed"], args
            state["washed"].add(well)
            state["wash_index"] += 1
            continue

        if name == "load-reader":
            counts[name] += 1
            assert len(args) == 2, args
            plate, reader = args
            assert plate == item["plate"], args
            assert reader == item["reader"], args
            assert state["incubated"], args
            assert len(state["washed"]) == len(wells), args
            assert not state["loaded"], args
            state["loaded"] = True
            continue

        if name == "read-well":
            counts["read"] += 1
            assert len(args) == 4, args
            well, next_well, plate, reader = args
            assert plate == item["plate"], args
            assert reader == item["reader"], args
            assert state["loaded"], args
            assert state["read_index"] < len(wells) - 1, args
            assert well == wells[state["read_index"]], args
            assert next_well == wells[state["read_index"] + 1], args
            assert well in state["washed"], args
            assert well not in state["readout"], args
            state["readout"].add(well)
            state["read_index"] += 1
            continue

        if name == "read-final-well":
            counts["read-final"] += 1
            assert len(args) == 3, args
            well, plate, reader = args
            assert plate == item["plate"], args
            assert reader == item["reader"], args
            assert state["loaded"], args
            assert state["read_index"] == len(wells) - 1, args
            assert well == wells[state["read_index"]], args
            assert well in state["washed"], args
            assert well not in state["readout"], args
            state["readout"].add(well)
            state["read_index"] += 1
            state["complete"] = True
            continue

        raise AssertionError(f"Unexpected action {name}")

    expected_well_count = len(wells)
    assert state["mix_index"] == expected_well_count, item["id"]
    assert state["wash_index"] == expected_well_count, item["id"]
    assert state["read_index"] == expected_well_count, item["id"]
    assert state["incubated"], item["id"]
    assert state["loaded"], item["id"]
    assert state["complete"], item["id"]
    assert state["aliquoted"] == well_set, item["id"]
    assert state["reagent_added"] == well_set, item["id"]
    assert state["mixed"] == well_set, item["id"]
    assert state["washed"] == well_set, item["id"]
    assert state["readout"] == well_set, item["id"]

    assert counts["aliquot-sample"] == expected_well_count, item["id"]
    assert counts["add-reagent"] == expected_well_count, item["id"]
    assert counts["mix"] + counts["mix-final"] == expected_well_count, item["id"]
    assert counts["mix-final"] == 1, item["id"]
    assert counts["incubate-plate"] == 1, item["id"]
    assert counts["wash"] + counts["wash-final"] == expected_well_count, item["id"]
    assert counts["wash-final"] == 1, item["id"]
    assert counts["load-reader"] == 1, item["id"]
    assert counts["read"] + counts["read-final"] == expected_well_count, item["id"]
    assert counts["read-final"] == 1, item["id"]
    assert len(actions) == expected_well_count * 5 + 2, item["id"]


def test_manifest_contains_primary_output():
    manifest = load_manifest()
    outputs = {item["plan_output"] for item in manifest}
    assert "assay_plans/batch_red_plan.txt" in outputs


def test_input_assets_exist_and_parse():
    manifest = load_manifest()
    for item in manifest:
        assert os.path.exists(app_path(item["domain"])), item["domain"]
        assert os.path.exists(app_path(item["problem"])), item["problem"]
        object_names = load_problem_objects(item)
        expected_names = {
            item["plate"],
            item["incubator"],
            item["washer"],
            item["reader"],
            *item["well_order"],
            *item["samples"],
            *item["reagents"],
        }
        assert expected_names.issubset(object_names), item["id"]


def test_primary_output_exists():
    assert os.path.exists(PRIMARY_OUTPUT)


def test_all_output_files_exist():
    manifest = load_manifest()
    for item in manifest:
        assert os.path.exists(app_path(item["plan_output"])), item["plan_output"]


def test_assay_plans_follow_pipeline_constraints():
    manifest = load_manifest()
    for item in manifest:
        plan_path = app_path(item["plan_output"])
        lines = read_plan_lines(plan_path)
        assert lines, f"Empty plan: {item['plan_output']}"
        actions = parse_actions(lines)
        object_names = load_problem_objects(item)
        simulate_batch(item, actions, object_names)
