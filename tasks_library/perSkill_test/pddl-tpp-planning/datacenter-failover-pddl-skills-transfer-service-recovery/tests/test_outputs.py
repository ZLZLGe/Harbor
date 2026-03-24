import json
import os
import re


APP_DIR = "/app"
MANIFEST_PATH = os.path.join(APP_DIR, "recovery_manifest.json")
PRIMARY_OUTPUT = os.path.join(APP_DIR, "recovery_plans/cluster_a_recovery.txt")
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
        args = [part.strip() for part in match.group(2).split(",") if part.strip()]
        actions.append((match.group(1), args))
    return actions


def expected_files_exist():
    manifest = load_manifest()
    for item in manifest:
        assert os.path.exists(app_path(item["domain"])), item["domain"]
        assert os.path.exists(app_path(item["problem"])), item["problem"]


def simulate_recovery(item, actions):
    state = {
        "link_restored": False,
        "promoted": False,
        "core_online": False,
        "edge_online": False,
        "cutover": False,
        "rebuilt": set(),
    }
    cutover_index = None

    for index, (name, args) in enumerate(actions):
        assert args, f"Missing args for {name}"

        if name == "restore-link":
            assert len(args) == 2, args
            cluster, standby_site = args
            assert cluster == item["cluster"], args
            assert standby_site == item["standby_site"], args
            assert not state["link_restored"], args
            state["link_restored"] = True
            continue

        if name == "promote-primary":
            assert len(args) == 2, args
            cluster, standby_site = args
            assert cluster == item["cluster"], args
            assert standby_site == item["standby_site"], args
            assert state["link_restored"], args
            assert not state["promoted"], args
            state["promoted"] = True
            continue

        if name == "restart-core-service":
            assert len(args) == 3, args
            cluster, service, standby_site = args
            assert cluster == item["cluster"], args
            assert service == item["core_service"], args
            assert standby_site == item["standby_site"], args
            assert state["promoted"], args
            assert not state["core_online"], args
            state["core_online"] = True
            continue

        if name == "restart-edge-service":
            assert len(args) == 4, args
            cluster, edge_service, core_service, standby_site = args
            assert cluster == item["cluster"], args
            assert edge_service == item["edge_service"], args
            assert core_service == item["core_service"], args
            assert standby_site == item["standby_site"], args
            assert state["core_online"], args
            assert not state["edge_online"], args
            state["edge_online"] = True
            continue

        if name == "cutover-traffic":
            assert len(args) == 4, args
            cluster, gateway, edge_service, standby_site = args
            assert cluster == item["cluster"], args
            assert gateway == item["gateway"], args
            assert edge_service == item["edge_service"], args
            assert standby_site == item["standby_site"], args
            assert state["link_restored"] and state["edge_online"], args
            assert not state["cutover"], args
            state["cutover"] = True
            cutover_index = index
            continue

        if name == "rebuild-replica":
            assert len(args) == 4, args
            cluster, replica, failed_site, standby_site = args
            assert cluster == item["cluster"], args
            assert replica in item["replicas"], args
            assert failed_site == item["failed_site"], args
            assert standby_site == item["standby_site"], args
            assert state["cutover"], args
            assert replica not in state["rebuilt"], args
            state["rebuilt"].add(replica)
            continue

        raise AssertionError(f"Unexpected action {name}")

    assert state["link_restored"], item["id"]
    assert state["promoted"], item["id"]
    assert state["core_online"], item["id"]
    assert state["edge_online"], item["id"]
    assert state["cutover"], item["id"]
    assert state["rebuilt"] == set(item["replicas"]), item["id"]
    assert cutover_index is not None, item["id"]

    expected_length = 5 + len(item["replicas"])
    assert len(actions) == expected_length, item["id"]

    for index, (name, _) in enumerate(actions):
        if name == "rebuild-replica":
            assert index > cutover_index, item["id"]


def test_manifest_contains_primary_output():
    manifest = load_manifest()
    outputs = {item["plan_output"] for item in manifest}
    assert "recovery_plans/cluster_a_recovery.txt" in outputs


def test_input_assets_exist():
    expected_files_exist()


def test_primary_output_exists():
    assert os.path.exists(PRIMARY_OUTPUT)


def test_all_output_files_exist():
    manifest = load_manifest()
    for item in manifest:
        assert os.path.exists(app_path(item["plan_output"])), item["plan_output"]


def test_recovery_plans_follow_failover_sequence():
    manifest = load_manifest()
    for item in manifest:
        lines = read_plan_lines(app_path(item["plan_output"]))
        assert lines, f"Empty plan: {item['plan_output']}"
        actions = parse_actions(lines)
        simulate_recovery(item, actions)
