from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))
OUTPUT_FILE = APP_ROOT / "output" / "branch_transit_audit.json"


@pytest.fixture(scope="module")
def output_data():
    assert OUTPUT_FILE.exists(), f"Output file {OUTPUT_FILE} does not exist"
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def test_output_structure(output_data):
    required = [
        "hub_cycle_detected",
        "hub_cycle",
        "affected_hubs",
        "branch_route_leak_detected",
        "branch_route_leaks",
        "policy_assessments",
        "rejected_forbidden_actions",
    ]
    for key in required:
        assert key in output_data, f"Missing required key {key}"


def test_cycle_detection(output_data):
    assert output_data["hub_cycle_detected"] is True
    assert output_data["hub_cycle"] == [65110, 65111]
    assert output_data["affected_hubs"] == [65110, 65111]


def test_route_leak_detection(output_data):
    assert output_data["branch_route_leak_detected"] is True
    leaks = output_data["branch_route_leaks"]
    assert isinstance(leaks, list)
    assert len(leaks) == 1
    leak = leaks[0]
    assert leak == {
        "leaker_as": 65110,
        "source_as": 65100,
        "destination_as": 65111,
        "source_type": "provider",
        "destination_type": "peer",
        "branch_id": "branch-bos",
        "prefix": "10.44.8.0/24",
    }


@pytest.mark.parametrize(
    "action,allowed,breaks_cycle,stops_leak,score",
    [
        (
            "Change BGP keepalive timer on the east hub gateway to 20 seconds and holdtime to 60 seconds",
            True,
            False,
            False,
            20,
        ),
        (
            "Apply export policy on east hub ASN 65110 to block provider-learned branch routes from core ASN 65100 toward peer west hub ASN 65111",
            True,
            False,
            True,
            60,
        ),
        (
            "Update east hub ASN 65110 so it no longer prefers migrating branch routes via west hub ASN 65111",
            True,
            True,
            False,
            60,
        ),
        (
            "Set route preference hierarchy on both hubs: local branches > core routes > peer hub routes",
            True,
            True,
            False,
            60,
        ),
        (
            "Enable Virtual WAN routing intent so inter-hub branch transit uses core ASN 65100 only",
            True,
            True,
            True,
            100,
        ),
        (
            "Configure no-export community on east hub for provider-learned branch prefixes before advertising to west hub peer",
            True,
            False,
            True,
            60,
        ),
        (
            "Install a user defined route override for migrating branch prefixes so forwarding uses the approved core path",
            True,
            True,
            True,
            100,
        ),
        (
            "Disable hub-to-hub branch connectivity between east hub and west hub",
            False,
            False,
            False,
            0,
        ),
        (
            "Shut down the west hub branch connection during the migration window",
            False,
            False,
            False,
            0,
        ),
        (
            "Enable route dampening for migrating branch prefixes on both hubs",
            True,
            False,
            False,
            20,
        ),
        (
            "Apply inbound AS-PATH filtering on west hub to reject core ASN 65100 when learned from east hub peer",
            True,
            False,
            True,
            60,
        ),
    ],
)
def test_policy_assessments(output_data, action, allowed, breaks_cycle, stops_leak, score):
    assessments = output_data["policy_assessments"]
    assert action in assessments, f"Missing assessment for {action}"
    assert assessments[action] == {
        "allowed": allowed,
        "breaks_cycle": breaks_cycle,
        "stops_leak": stops_leak,
        "score": score,
    }


def test_rejected_actions(output_data):
    rejected = output_data["rejected_forbidden_actions"]
    assert rejected == [
        "Disable hub-to-hub branch connectivity between east hub and west hub",
        "Shut down the west hub branch connection during the migration window",
    ]
