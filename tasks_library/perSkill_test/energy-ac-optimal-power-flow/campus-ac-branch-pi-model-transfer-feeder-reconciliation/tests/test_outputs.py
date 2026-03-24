import json
import math
from pathlib import Path


TOL = 1e-6


def resolve(path_in_root: str, local_fallback: str) -> Path:
    primary = Path(path_in_root)
    try:
        exists = primary.exists()
    except PermissionError:
        exists = False
    if exists:
        return primary
    return Path(local_fallback)


def load_topology() -> dict:
    path = resolve("/root/campus_feeder_topology.json", "environment/campus_feeder_topology.json")
    return json.loads(path.read_text())


def load_snapshot() -> dict:
    path = resolve("/root/campus_operating_snapshot.json", "environment/campus_operating_snapshot.json")
    return json.loads(path.read_text())


def load_output() -> dict:
    path = resolve("/root/feeder_reconciliation.json", "feeder_reconciliation.json")
    if not path.exists():
        raise AssertionError("feeder_reconciliation.json was not created")
    return json.loads(path.read_text())


def rounded(value: float) -> float:
    return round(float(value), 6)


def approx_equal(left: float, right: float, tol: float = TOL) -> None:
    assert math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tol), (left, right)


def branch_flow(branch: dict, voltage_by_bus: dict[int, tuple[float, float]], base_mva: float) -> dict:
    vm_i, va_i_deg = voltage_by_bus[int(branch["from_bus"])]
    vm_j, va_j_deg = voltage_by_bus[int(branch["to_bus"])]
    tap = float(branch["tap"]) if abs(float(branch["tap"])) >= 1e-12 else 1.0
    shift = math.radians(float(branch["shift_deg"]))
    r = float(branch["r_pu"])
    x = float(branch["x_pu"])
    bc = float(branch["b_pu"])

    if abs(r) < 1e-12 and abs(x) < 1e-12:
        g = 0.0
        b = 0.0
    else:
        denom = r * r + x * x
        g = r / denom
        b = -x / denom

    va_i = math.radians(va_i_deg)
    va_j = math.radians(va_j_deg)
    inv_t = 1.0 / tap
    inv_t2 = inv_t * inv_t

    delta_ij = va_i - va_j - shift
    p_from_pu = g * vm_i * vm_i * inv_t2 - vm_i * vm_j * inv_t * (
        g * math.cos(delta_ij) + b * math.sin(delta_ij)
    )
    q_from_pu = -(b + bc / 2.0) * vm_i * vm_i * inv_t2 - vm_i * vm_j * inv_t * (
        g * math.sin(delta_ij) - b * math.cos(delta_ij)
    )

    delta_ji = va_j - va_i + shift
    p_to_pu = g * vm_j * vm_j - vm_i * vm_j * inv_t * (
        g * math.cos(delta_ji) + b * math.sin(delta_ji)
    )
    q_to_pu = -(b + bc / 2.0) * vm_j * vm_j - vm_i * vm_j * inv_t * (
        g * math.sin(delta_ji) - b * math.cos(delta_ji)
    )

    p_from_mw = p_from_pu * base_mva
    q_from_mvar = q_from_pu * base_mva
    p_to_mw = p_to_pu * base_mva
    q_to_mvar = q_to_pu * base_mva

    return {
        "id": branch["id"],
        "from_bus": int(branch["from_bus"]),
        "to_bus": int(branch["to_bus"]),
        "p_from_MW": p_from_mw,
        "q_from_MVAr": q_from_mvar,
        "s_from_MVA": math.hypot(p_from_mw, q_from_mvar),
        "p_to_MW": p_to_mw,
        "q_to_MVAr": q_to_mvar,
        "s_to_MVA": math.hypot(p_to_mw, q_to_mvar),
        "p_loss_MW": p_from_mw + p_to_mw,
        "q_loss_MVAr": q_from_mvar + q_to_mvar,
    }


def expected_output(topology: dict, snapshot: dict) -> dict:
    base_mva = float(topology["baseMVA"])
    voltage_by_bus = {
        int(item["bus"]): (float(item["vm_pu"]), float(item["va_deg"]))
        for item in snapshot["bus_voltages"]
    }
    measurement_by_bus = {int(item["bus"]): item for item in snapshot["bus_measurements"]}
    branch_out_by_bus = {
        int(item["id"]): {"p_branch_out_MW": 0.0, "q_branch_out_MVAr": 0.0}
        for item in topology["buses"]
    }

    branch_losses = []
    for branch in topology["branches"]:
        record = branch_flow(branch, voltage_by_bus, base_mva)
        branch_losses.append(record)
        branch_out_by_bus[record["from_bus"]]["p_branch_out_MW"] += record["p_from_MW"]
        branch_out_by_bus[record["from_bus"]]["q_branch_out_MVAr"] += record["q_from_MVAr"]
        branch_out_by_bus[record["to_bus"]]["p_branch_out_MW"] += record["p_to_MW"]
        branch_out_by_bus[record["to_bus"]]["q_branch_out_MVAr"] += record["q_to_MVAr"]

    branch_losses.sort(key=lambda item: (-item["p_loss_MW"], -item["q_loss_MVAr"], item["id"]))
    for index, item in enumerate(branch_losses, start=1):
        item["loss_rank"] = index
    raw_branch_losses = list(branch_losses)
    branch_losses = [
        {
            "loss_rank": item["loss_rank"],
            "id": item["id"],
            "from_bus": item["from_bus"],
            "to_bus": item["to_bus"],
            "p_from_MW": rounded(item["p_from_MW"]),
            "q_from_MVAr": rounded(item["q_from_MVAr"]),
            "s_from_MVA": rounded(item["s_from_MVA"]),
            "p_to_MW": rounded(item["p_to_MW"]),
            "q_to_MVAr": rounded(item["q_to_MVAr"]),
            "s_to_MVA": rounded(item["s_to_MVA"]),
            "p_loss_MW": rounded(item["p_loss_MW"]),
            "q_loss_MVAr": rounded(item["q_loss_MVAr"]),
        }
        for item in branch_losses
    ]

    bus_reconciliation = []
    for bus in sorted(topology["buses"], key=lambda item: int(item["id"])):
        bus_id = int(bus["id"])
        vm_pu, va_deg = voltage_by_bus[bus_id]
        measurement = measurement_by_bus[bus_id]
        branch_out = branch_out_by_bus[bus_id]
        p_known = float(measurement["p_feeder_head_import_MW"]) + float(measurement["p_distributed_generation_MW"])
        q_known = float(measurement["q_feeder_head_import_MVAr"]) + float(measurement["q_distributed_generation_MVAr"])
        p_shunt = float(bus["gs_MW_at_1pu"]) * vm_pu * vm_pu
        q_shunt = float(bus["bs_MVAr_at_1pu"]) * vm_pu * vm_pu
        p_residual = p_known - float(measurement["p_load_MW"]) - p_shunt - branch_out["p_branch_out_MW"]
        q_residual = q_known - float(measurement["q_load_MVAr"]) + q_shunt - branch_out["q_branch_out_MVAr"]
        bus_reconciliation.append(
            {
                "bus": bus_id,
                "name": bus["name"],
                "vm_pu": rounded(vm_pu),
                "va_deg": rounded(va_deg),
                "p_load_MW": rounded(measurement["p_load_MW"]),
                "q_load_MVAr": rounded(measurement["q_load_MVAr"]),
                "p_feeder_head_import_MW": rounded(measurement["p_feeder_head_import_MW"]),
                "q_feeder_head_import_MVAr": rounded(measurement["q_feeder_head_import_MVAr"]),
                "p_distributed_generation_MW": rounded(measurement["p_distributed_generation_MW"]),
                "q_distributed_generation_MVAr": rounded(measurement["q_distributed_generation_MVAr"]),
                "p_known_injection_MW": rounded(p_known),
                "q_known_injection_MVAr": rounded(q_known),
                "p_shunt_consumption_MW": rounded(p_shunt),
                "q_shunt_injection_MVAr": rounded(q_shunt),
                "p_branch_out_MW": rounded(branch_out["p_branch_out_MW"]),
                "q_branch_out_MVAr": rounded(branch_out["q_branch_out_MVAr"]),
                "p_residual_MW": rounded(p_residual),
                "q_residual_MVAr": rounded(q_residual),
                "apparent_imbalance_MVA": rounded(math.hypot(p_residual, q_residual)),
            }
        )

    top_imbalances_source = sorted(
        bus_reconciliation,
        key=lambda item: (-item["apparent_imbalance_MVA"], -abs(item["q_residual_MVAr"]), item["bus"]),
    )[:3]
    top_imbalances = [
        {
            "rank": index,
            "bus": item["bus"],
            "name": item["name"],
            "p_residual_MW": item["p_residual_MW"],
            "q_residual_MVAr": item["q_residual_MVAr"],
            "apparent_imbalance_MVA": item["apparent_imbalance_MVA"],
        }
        for index, item in enumerate(top_imbalances_source, start=1)
    ]

    return {
        "study_id": topology["study_id"],
        "summary": {
            "baseMVA": rounded(base_mva),
            "bus_count": len(topology["buses"]),
            "branch_count": len(topology["branches"]),
            "total_measured_load_MW": rounded(
                sum(float(item["p_load_MW"]) for item in snapshot["bus_measurements"])
            ),
            "total_measured_load_MVAr": rounded(
                sum(float(item["q_load_MVAr"]) for item in snapshot["bus_measurements"])
            ),
            "total_known_injection_MW": rounded(
                sum(
                    float(item["p_feeder_head_import_MW"]) + float(item["p_distributed_generation_MW"])
                    for item in snapshot["bus_measurements"]
                )
            ),
            "total_known_injection_MVAr": rounded(
                sum(
                    float(item["q_feeder_head_import_MVAr"]) + float(item["q_distributed_generation_MVAr"])
                    for item in snapshot["bus_measurements"]
                )
            ),
            "total_branch_loss_MW": rounded(sum(item["p_loss_MW"] for item in raw_branch_losses)),
            "total_branch_loss_MVAr": rounded(sum(item["q_loss_MVAr"] for item in raw_branch_losses)),
            "max_p_residual_MW": rounded(max(abs(item["p_residual_MW"]) for item in bus_reconciliation)),
            "max_q_residual_MVAr": rounded(max(abs(item["q_residual_MVAr"]) for item in bus_reconciliation)),
            "worst_bus": top_imbalances[0]["bus"],
            "worst_apparent_imbalance_MVA": top_imbalances[0]["apparent_imbalance_MVA"],
        },
        "branch_losses": branch_losses,
        "bus_reconciliation": bus_reconciliation,
        "top_imbalances": top_imbalances,
    }


def test_schema(output: dict) -> None:
    assert output["study_id"] == "campus-feeder-recon-2034-09-15T07:30:00+08:00"
    assert isinstance(output["summary"], dict)
    assert isinstance(output["branch_losses"], list)
    assert isinstance(output["bus_reconciliation"], list)
    assert isinstance(output["top_imbalances"], list)
    assert len(output["branch_losses"]) == 5
    assert len(output["bus_reconciliation"]) == 6
    assert len(output["top_imbalances"]) == 3


def test_values(output: dict, expected: dict) -> None:
    assert output["study_id"] == expected["study_id"]

    for key, value in expected["summary"].items():
        if isinstance(value, int):
            assert output["summary"][key] == value
        else:
            approx_equal(output["summary"][key], value)

    for actual, reference in zip(output["branch_losses"], expected["branch_losses"]):
        assert actual["loss_rank"] == reference["loss_rank"]
        assert actual["id"] == reference["id"]
        assert actual["from_bus"] == reference["from_bus"]
        assert actual["to_bus"] == reference["to_bus"]
        for key in (
            "p_from_MW",
            "q_from_MVAr",
            "s_from_MVA",
            "p_to_MW",
            "q_to_MVAr",
            "s_to_MVA",
            "p_loss_MW",
            "q_loss_MVAr",
        ):
            approx_equal(actual[key], reference[key])

    for actual, reference in zip(output["bus_reconciliation"], expected["bus_reconciliation"]):
        assert actual["bus"] == reference["bus"]
        assert actual["name"] == reference["name"]
        for key in (
            "vm_pu",
            "va_deg",
            "p_load_MW",
            "q_load_MVAr",
            "p_feeder_head_import_MW",
            "q_feeder_head_import_MVAr",
            "p_distributed_generation_MW",
            "q_distributed_generation_MVAr",
            "p_known_injection_MW",
            "q_known_injection_MVAr",
            "p_shunt_consumption_MW",
            "q_shunt_injection_MVAr",
            "p_branch_out_MW",
            "q_branch_out_MVAr",
            "p_residual_MW",
            "q_residual_MVAr",
            "apparent_imbalance_MVA",
        ):
            approx_equal(actual[key], reference[key])

    for actual, reference in zip(output["top_imbalances"], expected["top_imbalances"]):
        assert actual["rank"] == reference["rank"]
        assert actual["bus"] == reference["bus"]
        assert actual["name"] == reference["name"]
        for key in ("p_residual_MW", "q_residual_MVAr", "apparent_imbalance_MVA"):
            approx_equal(actual[key], reference[key])


def test_sorting(output: dict) -> None:
    branch_order = [(item["p_loss_MW"], item["q_loss_MVAr"], item["id"]) for item in output["branch_losses"]]
    expected_branch_order = sorted(branch_order, key=lambda item: (-item[0], -item[1], item[2]))
    assert branch_order == expected_branch_order

    bus_order = [item["bus"] for item in output["bus_reconciliation"]]
    assert bus_order == sorted(bus_order)

    imbalance_order = [
        (item["apparent_imbalance_MVA"], abs(item["q_residual_MVAr"]), item["bus"])
        for item in output["top_imbalances"]
    ]
    expected_imbalance_order = sorted(imbalance_order, key=lambda item: (-item[0], -item[1], item[2]))
    assert imbalance_order == expected_imbalance_order


def main() -> None:
    topology = load_topology()
    snapshot = load_snapshot()
    output = load_output()
    expected = expected_output(topology, snapshot)

    test_schema(output)
    test_values(output, expected)
    test_sorting(output)

    print("feeder reconciliation checks passed")


if __name__ == "__main__":
    main()
