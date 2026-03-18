from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))
OUTPUT_FILE = APP_ROOT / "output" / "nva_transit_containment.json"


@pytest.fixture(scope="module")
def output_data():
    assert OUTPUT_FILE.exists(), f"Output file {OUTPUT_FILE} does not exist"
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def test_output_structure(output_data):
    required = [
        "nva_cycle_detected",
        "nva_cycle",
        "affected_nvas",
        "provider_route_leak_detected",
        "provider_route_leaks",
        "mitigation_assessments",
        "forbidden_actions",
    ]
    for key in required:
        assert key in output_data, f"Missing required key {key}"


def test_cycle_detection(output_data):
    assert output_data["nva_cycle_detected"] is True
    assert output_data["nva_cycle"] == [65210, 65211]
    assert output_data["affected_nvas"] == [65210, 65211]


def test_provider_route_leak_detection(output_data):
    assert output_data["provider_route_leak_detected"] is True
    leaks = output_data["provider_route_leaks"]
    assert isinstance(leaks, list)
    assert len(leaks) == 1
    assert leaks[0] == {
        "leaker_as": 65210,
        "source_as": 65200,
        "destination_as": 65211,
        "source_type": "provider",
        "destination_type": "peer",
        "prefix": "10.77.32.0/24",
        "origin_asn": 65231,
        "route_server": "ars-prod-eastus",
    }


@pytest.mark.parametrize(
    "action,allowed,breaks_cycle,stops_leak,score",
    [
        (
            "Tune the BGP keepalive timer on NVA-A to 15 seconds and holdtime to 45 seconds",
            True,
            False,
            False,
            20,
        ),
        (
            "Configure an outbound route map on NVA-A ASN 65210 to block Azure Route Server-learned prefixes from ASN 65200 before advertising them to NVA-B ASN 65211",
            True,
            False,
            True,
            60,
        ),
        (
            "Update NVA-A ASN 65210 so it no longer prefers the analytics spoke prefix via NVA-B ASN 65211",
            True,
            True,
            False,
            60,
        ),
        (
            "Set NVA route preference hierarchy to local spokes > Azure Route Server > NVA peer transit",
            True,
            True,
            False,
            60,
        ),
        (
            "Apply no-export community on Azure Route Server-learned prefixes when NVA-A advertises to NVA-B",
            True,
            False,
            True,
            60,
        ),
        (
            "Install a user defined route for 10.77.32.0/24 so secured spokes use the approved Route Server path instead of NVA peer transit",
            True,
            True,
            True,
            100,
        ),
        (
            "Apply inbound AS-PATH filtering on NVA-B to reject ASN 65200 when received from NVA-A peer",
            True,
            False,
            True,
            60,
        ),
        (
            "Clear the NVA peer preference override and enforce an export filter that blocks Route Server-learned prefixes toward the peer",
            True,
            True,
            True,
            100,
        ),
        (
            "Enable ECMP across both NVAs for the analytics spoke prefix",
            True,
            False,
            False,
            20,
        ),
        (
            "Disable the BGP peering between Azure Route Server and NVA-B",
            False,
            False,
            False,
            0,
        ),
        (
            "Shut down the NVA peer transit interface during the incident",
            False,
            False,
            False,
            0,
        ),
        (
            "Constrain NVA-A with an inbound prefix list from NVA-B so only local spoke routes are accepted from the peer",
            True,
            True,
            False,
            60,
        ),
    ],
)
def test_mitigation_assessments(output_data, action, allowed, breaks_cycle, stops_leak, score):
    assessments = output_data["mitigation_assessments"]
    assert action in assessments, f"Missing assessment for {action}"
    assert assessments[action] == {
        "allowed": allowed,
        "breaks_cycle": breaks_cycle,
        "stops_leak": stops_leak,
        "score": score,
    }


def test_forbidden_actions(output_data):
    assert output_data["forbidden_actions"] == [
        "Disable the BGP peering between Azure Route Server and NVA-B",
        "Shut down the NVA peer transit interface during the incident",
    ]
