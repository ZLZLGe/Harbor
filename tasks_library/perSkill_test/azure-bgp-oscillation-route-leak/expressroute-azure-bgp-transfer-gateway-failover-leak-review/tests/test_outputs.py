from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))
OUTPUT_FILE = APP_ROOT / "output" / "failover_leak_review.json"


@pytest.fixture(scope="module")
def output_data():
    assert OUTPUT_FILE.exists(), f"Output file {OUTPUT_FILE} does not exist"
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def test_output_structure(output_data):
    required = [
        "failover_cycle_detected",
        "failover_cycle",
        "affected_gateways",
        "upstream_route_leak_detected",
        "upstream_route_leaks",
        "remediation_assessments",
        "forbidden_actions",
    ]
    for key in required:
        assert key in output_data, f"Missing required key {key}"


def test_cycle_detection(output_data):
    assert output_data["failover_cycle_detected"] is True
    assert output_data["failover_cycle"] == [65310, 65311]
    assert output_data["affected_gateways"] == [65310, 65311]


def test_upstream_route_leak_detection(output_data):
    assert output_data["upstream_route_leak_detected"] is True
    leaks = output_data["upstream_route_leaks"]
    assert isinstance(leaks, list)
    assert len(leaks) == 1
    assert leaks[0] == {
        "leaker_as": 65310,
        "source_as": 65300,
        "destination_as": 65311,
        "source_type": "provider",
        "destination_type": "peer",
        "prefix": "10.88.30.0/24",
        "origin_asn": 65330,
        "path_label": "ExpressRoute-to-VPN backup peer",
    }


@pytest.mark.parametrize(
    "action,allowed,breaks_cycle,stops_leak,score",
    [
        (
            "Tune BGP keepalive on the ExpressRoute customer edge to 10 seconds and holdtime to 30 seconds",
            True,
            False,
            False,
            20,
        ),
        (
            "Apply an outbound filter on the ExpressRoute customer edge ASN 65310 to block Azure-edge-learned routes from ASN 65300 before advertising them to VPN peer ASN 65311",
            True,
            False,
            True,
            60,
        ),
        (
            "Update the ExpressRoute failover policy so ASN 65310 no longer prefers branch-hou prefix 10.88.30.0/24 via VPN peer ASN 65311",
            True,
            True,
            False,
            60,
        ),
        (
            "Set failover preference hierarchy to local branch routes > ExpressRoute primary > VPN backup peer paths",
            True,
            True,
            False,
            60,
        ),
        (
            "Apply no-export community on Azure-edge-learned routes before the ExpressRoute customer edge advertises them to the VPN peer",
            True,
            False,
            True,
            60,
        ),
        (
            "Install a user defined route override for 10.88.30.0/24 so Azure subnets use the approved ExpressRoute next hop during failover",
            True,
            True,
            True,
            100,
        ),
        (
            "Apply inbound AS-PATH filtering on the VPN customer edge to reject Azure edge ASN 65300 when received from the ExpressRoute peer",
            True,
            False,
            True,
            60,
        ),
        (
            "Clear the failover preference override and pair it with an export filter that blocks Azure-edge-learned routes toward the VPN peer",
            True,
            True,
            True,
            100,
        ),
        (
            "Enable ECMP across ExpressRoute and VPN for the branch-hou prefix during failover",
            True,
            False,
            False,
            20,
        ),
        (
            "Disable the ExpressRoute and VPN gateway peering during the incident",
            False,
            False,
            False,
            0,
        ),
        (
            "Attach a custom route map directly to the Azure VPN gateway to suppress provider-learned prefixes",
            False,
            False,
            False,
            0,
        ),
        (
            "Shut down the VPN gateway connection until the leak alarm clears",
            False,
            False,
            False,
            0,
        ),
    ],
)
def test_remediation_assessments(output_data, action, allowed, breaks_cycle, stops_leak, score):
    assessments = output_data["remediation_assessments"]
    assert action in assessments, f"Missing assessment for {action}"
    assert assessments[action] == {
        "allowed": allowed,
        "breaks_cycle": breaks_cycle,
        "stops_leak": stops_leak,
        "score": score,
    }


def test_forbidden_actions(output_data):
    assert output_data["forbidden_actions"] == [
        "Attach a custom route map directly to the Azure VPN gateway to suppress provider-learned prefixes",
        "Disable the ExpressRoute and VPN gateway peering during the incident",
        "Shut down the VPN gateway connection until the leak alarm clears",
    ]
