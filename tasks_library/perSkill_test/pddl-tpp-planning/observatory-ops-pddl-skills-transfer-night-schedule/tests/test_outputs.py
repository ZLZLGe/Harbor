import json
import os
import re


APP_DIR = "/app"
MANIFEST_PATH = os.path.join(APP_DIR, "night_windows.json")
PRIMARY_OUTPUT = os.path.join(APP_DIR, "observatory_plans/night_window_plan.txt")
ACTION_RE = re.compile(r"^([a-z0-9-]+)\(([^)]*)\)$")


def load_manifest():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def app_path(relative_path):
    return os.path.join(APP_DIR, relative_path)


def parse_problem(problem_path):
    with open(problem_path, "r", encoding="utf-8") as handle:
        lines = [line.rstrip() for line in handle]

    objects = {}
    object_names = set()
    init_facts = set()
    goal_facts = set()
    section = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("(:objects"):
            section = "objects"
            continue
        if line.startswith("(:init"):
            section = "init"
            continue
        if line.startswith("(:goal"):
            section = "goal"
            continue
        if line == "(:domain observatory-night)":
            continue
        if line in {")", "))", ")))"}:
            section = None
            continue
        if section == "objects":
            names_part, _, type_name = line.rpartition(" - ")
            members = [token for token in names_part.split() if token]
            type_name = type_name.strip().rstrip(")")
            objects.setdefault(type_name, set()).update(members)
            object_names.update(members)
            continue
        if section == "init":
            if line.startswith("(") and line.endswith(")"):
                tokens = parse_atom_line(line)
                init_facts.add(tokens)
            continue
        if section == "goal":
            if line.startswith("(and"):
                continue
            if line.startswith("(") and line.endswith(")"):
                tokens = parse_atom_line(line)
                goal_facts.add(tokens)

    return {
        "objects": objects,
        "object_names": object_names,
        "init_facts": init_facts,
        "goal_facts": goal_facts,
    }


def parse_atom_line(line):
    cleaned = line
    while cleaned.endswith(")"):
        cleaned = cleaned[:-1]
        if not cleaned.startswith("("):
            break
    assert cleaned.startswith("("), f"Invalid atom line: {line}"
    return tuple(cleaned[1:].split())


def read_plan_lines(plan_path):
    with open(plan_path, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle.readlines() if line.strip()]


def parse_actions(plan_lines):
    actions = []
    for line in plan_lines:
        match = ACTION_RE.match(line)
        assert match, f"Invalid action syntax: {line}"
        args = [part.strip() for part in match.group(2).split(",") if part.strip()]
        actions.append((match.group(1), args))
    return actions


def build_state(problem):
    init_facts = problem["init_facts"]
    current_attitude = {}
    current_slots = []
    next_slots = {}
    points_at = {}
    relay_attitudes = set()
    target_visible = set()
    link_visible = set()
    slew_links = set()
    stable = set()
    buffer_free = set()
    requested = set()

    for fact in init_facts:
        predicate = fact[0]
        if predicate == "current-attitude":
            _, telescope, attitude = fact
            current_attitude[telescope] = attitude
        elif predicate == "current-slot":
            _, slot = fact
            current_slots.append(slot)
        elif predicate == "next-slot":
            _, nxt, current = fact
            next_slots[current] = nxt
        elif predicate == "points-at":
            _, attitude, target = fact
            points_at[attitude] = target
        elif predicate == "relay-attitude":
            _, attitude = fact
            relay_attitudes.add(attitude)
        elif predicate == "target-visible":
            _, target, slot = fact
            target_visible.add((target, slot))
        elif predicate == "link-visible":
            _, slot = fact
            link_visible.add(slot)
        elif predicate == "slew-link":
            _, origin, destination = fact
            slew_links.add((origin, destination))
        elif predicate == "stable":
            _, telescope = fact
            stable.add(telescope)
        elif predicate == "buffer-free":
            _, telescope = fact
            buffer_free.add(telescope)
        elif predicate == "requested":
            _, target = fact
            requested.add(target)

    assert len(current_slots) == 1

    return {
        "current_attitude": current_attitude,
        "current_slot": current_slots[0],
        "next_slots": next_slots,
        "points_at": points_at,
        "relay_attitudes": relay_attitudes,
        "target_visible": target_visible,
        "link_visible": link_visible,
        "slew_links": slew_links,
        "stable": stable,
        "buffer_free": buffer_free,
        "requested": requested,
        "captured": set(),
        "sent": set(),
    }


def require_known_objects(problem, args):
    unknown = [arg for arg in args if arg not in problem["object_names"]]
    assert not unknown, f"Unknown objects in plan: {unknown}"


def advance_slot(state, current_slot, next_slot):
    assert state["current_slot"] == current_slot, f"Expected current slot {state['current_slot']}, got {current_slot}"
    expected_next = state["next_slots"].get(current_slot)
    assert expected_next == next_slot, f"Invalid slot transition {current_slot}->{next_slot}"
    state["current_slot"] = next_slot


def simulate_plan(problem, manifest_item, actions):
    state = build_state(problem)
    action_counts = {"slew": 0, "calibrate": 0, "observe": 0, "downlink": 0}

    for name, args in actions:
        require_known_objects(problem, args)
        assert name in action_counts, f"Unexpected action {name}"
        action_counts[name] += 1

        if name == "slew":
            telescope, origin, destination, current_slot, next_slot = args
            assert state["current_attitude"].get(telescope) == origin, args
            assert (origin, destination) in state["slew_links"], args
            advance_slot(state, current_slot, next_slot)
            state["current_attitude"][telescope] = destination
            state["stable"].discard(telescope)
            continue

        if name == "calibrate":
            telescope, attitude, current_slot, next_slot = args
            assert state["current_attitude"].get(telescope) == attitude, args
            advance_slot(state, current_slot, next_slot)
            state["stable"].add(telescope)
            continue

        if name == "observe":
            telescope, target, attitude, current_slot, next_slot = args
            assert state["current_attitude"].get(telescope) == attitude, args
            assert state["points_at"].get(attitude) == target, args
            assert telescope in state["stable"], args
            assert telescope in state["buffer_free"], args
            assert target in state["requested"], args
            assert (target, current_slot) in state["target_visible"], args
            advance_slot(state, current_slot, next_slot)
            state["captured"].add(target)
            state["buffer_free"].discard(telescope)
            continue

        telescope, target, attitude, current_slot, next_slot = args
        assert state["current_attitude"].get(telescope) == attitude, args
        assert attitude in state["relay_attitudes"], args
        assert target in state["captured"], args
        assert current_slot in state["link_visible"], args
        advance_slot(state, current_slot, next_slot)
        state["captured"].remove(target)
        state["requested"].discard(target)
        state["sent"].add(target)
        state["buffer_free"].add(telescope)

    required_goals = {
        target
        for predicate, target in problem["goal_facts"]
        if predicate == "sent"
    }
    assert required_goals.issubset(state["sent"]), f"Missing goals: {sorted(required_goals - state['sent'])}"
    assert set(manifest_item["required_targets"]) == required_goals
    assert action_counts["observe"] == len(manifest_item["required_targets"])
    assert action_counts["downlink"] == len(manifest_item["required_targets"])
    assert action_counts["calibrate"] == len(manifest_item["required_targets"])
    assert action_counts["slew"] == len(manifest_item["required_targets"]) * 2


def test_manifest_contains_primary_output():
    manifest = load_manifest()
    outputs = {item["plan_output"] for item in manifest}
    assert "observatory_plans/night_window_plan.txt" in outputs


def test_primary_output_exists():
    assert os.path.exists(PRIMARY_OUTPUT)


def test_all_output_files_exist():
    manifest = load_manifest()
    for item in manifest:
        assert os.path.exists(app_path(item["plan_output"])), item["plan_output"]


def test_plans_satisfy_observatory_constraints():
    manifest = load_manifest()
    for item in manifest:
        problem = parse_problem(app_path(item["problem"]))
        plan_lines = read_plan_lines(app_path(item["plan_output"]))
        assert plan_lines, f"Empty plan: {item['plan_output']}"
        actions = parse_actions(plan_lines)
        simulate_plan(problem, item, actions)
