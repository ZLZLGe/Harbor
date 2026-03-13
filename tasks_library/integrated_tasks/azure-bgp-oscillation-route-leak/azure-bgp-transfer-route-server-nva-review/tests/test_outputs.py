from pathlib import Path
import json
import os

import pytest

OUTPUT_FILE = Path(os.environ.get("TASK_OUTPUT_FILE", "/app/output/route_server_reflection_review.json"))


@pytest.fixture(scope="module")
def output_data():
    assert OUTPUT_FILE.exists(), f"Output file {OUTPUT_FILE} does not exist"
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


class TestStructure:
    def test_required_top_level_keys(self, output_data):
        required_keys = {
            "review_summary",
            "incidents",
            "effective_changes",
            "rejected_actions",
            "action_results",
        }
        assert required_keys.issubset(output_data.keys())

    def test_review_summary(self, output_data):
        assert output_data["review_summary"] == {
            "customer_prefix": "172.18.44.0/24",
            "route_server_as": 65515,
            "oscillation_detected": True,
            "route_leak_detected": True,
        }

    def test_incidents(self, output_data):
        incidents = output_data["incidents"]
        assert isinstance(incidents, list)
        assert len(incidents) == 3

        assert incidents[0] == {
            "incident_type": "oscillation",
            "prefix": "172.18.44.0/24",
            "participants": [65110, 65111],
            "details": {
                "cycle": [65110, 65111],
                "reflected_by": 65515,
            },
        }

        leak_tuples = [
            (
                incident["details"]["leaker_as"],
                incident["details"]["source_as"],
                incident["details"]["destination_as"],
                incident["details"]["source_type"],
                incident["details"]["destination_type"],
                tuple(incident["participants"]),
                incident["prefix"],
            )
            for incident in incidents[1:]
        ]

        assert leak_tuples == [
            (65110, 65515, 65111, "provider", "peer", (65110, 65111, 65515), "0.0.0.0/0"),
            (65111, 65515, 65110, "provider", "peer", (65110, 65111, 65515), "10.250.0.0/16"),
        ]

    def test_effective_changes(self, output_data):
        assert output_data["effective_changes"] == [
            {
                "action": "Apply a symmetric route policy package on nva-east and nva-west: stop preferring customer prefix 172.18.44.0/24 via the opposite appliance and block Route Server-learned prefixes from appliance-to-appliance export",
                "addresses": ["oscillation", "route_leak"],
            },
            {
                "action": "Install UDR next-hop overrides on both spoke route tables so 172.18.44.0/24 always uses the approved active NVA instead of a reflected appliance path",
                "addresses": ["oscillation"],
            },
            {
                "action": "Update nva-east local preference so customer prefix 172.18.44.0/24 no longer prefers the reflected path via nva-west",
                "addresses": ["oscillation"],
            },
            {
                "action": "Raise local preference of directly attached branch routes above reflected appliance routes on both NVAs for 172.18.44.0/24",
                "addresses": ["oscillation"],
            },
            {
                "action": "Apply export policy on both NVAs to block every Route Server-learned prefix from being advertised to the opposite appliance",
                "addresses": ["route_leak"],
            },
            {
                "action": "Stamp a no-export community on every Route Server-learned prefix before either NVA re-advertises it to the opposite appliance",
                "addresses": ["route_leak"],
            },
            {
                "action": "Publish a single approved next hop for 172.18.44.0/24 on both NVAs and attach export filters for all Route Server-learned routes",
                "addresses": ["oscillation", "route_leak"],
            },
        ]

    def test_rejected_actions(self, output_data):
        assert output_data["rejected_actions"] == [
            {
                "action": "Disable the Route Server BGP peering with nva-west until the incident is over",
                "reason": "prohibited_connectivity_teardown",
            },
            {
                "action": "Remove nva-east from the Azure Route Server peering set to stop reflection immediately",
                "reason": "prohibited_connectivity_teardown",
            },
            {
                "action": "Shut down the standby data interface on nva-west",
                "reason": "prohibited_connectivity_teardown",
            },
            {
                "action": "Restart the BGP daemon on both NVAs and clear all reflected routes",
                "reason": "operational_reset_only",
            },
        ]


class TestActionResults:
    EXPECTATIONS = [
        (
            "Apply a symmetric route policy package on nva-east and nva-west: stop preferring customer prefix 172.18.44.0/24 via the opposite appliance and block Route Server-learned prefixes from appliance-to-appliance export",
            True,
            ["oscillation", "route_leak"],
        ),
        (
            "Install UDR next-hop overrides on both spoke route tables so 172.18.44.0/24 always uses the approved active NVA instead of a reflected appliance path",
            True,
            ["oscillation"],
        ),
        (
            "Update nva-east local preference so customer prefix 172.18.44.0/24 no longer prefers the reflected path via nva-west",
            True,
            ["oscillation"],
        ),
        (
            "Raise local preference of directly attached branch routes above reflected appliance routes on both NVAs for 172.18.44.0/24",
            True,
            ["oscillation"],
        ),
        (
            "Apply export policy on both NVAs to block every Route Server-learned prefix from being advertised to the opposite appliance",
            True,
            ["route_leak"],
        ),
        (
            "Stamp a no-export community on every Route Server-learned prefix before either NVA re-advertises it to the opposite appliance",
            True,
            ["route_leak"],
        ),
        (
            "Apply export policy only on nva-east to stop advertising Route Server-learned prefixes to nva-west",
            True,
            [],
        ),
        (
            "Apply ingress filtering on nva-west to reject only 0.0.0.0/0 when it is received from nva-east",
            True,
            [],
        ),
        (
            "Change BGP keepalive to 15 seconds and hold time to 45 seconds on both NVAs",
            True,
            [],
        ),
        (
            "Enable route dampening on nva-west with suppress limit 2000 and reuse 750",
            True,
            [],
        ),
        (
            "Set MED 30 on nva-east advertisements reflected through Route Server",
            True,
            [],
        ),
        (
            "Disable the Route Server BGP peering with nva-west until the incident is over",
            False,
            [],
        ),
        (
            "Remove nva-east from the Azure Route Server peering set to stop reflection immediately",
            False,
            [],
        ),
        (
            "Shut down the standby data interface on nva-west",
            False,
            [],
        ),
        (
            "Restart the BGP daemon on both NVAs and clear all reflected routes",
            False,
            [],
        ),
        (
            "Publish a single approved next hop for 172.18.44.0/24 on both NVAs and attach export filters for all Route Server-learned routes",
            True,
            ["oscillation", "route_leak"],
        ),
    ]

    @pytest.mark.parametrize("action_name,expected_allowed,expected_addresses", EXPECTATIONS)
    def test_action_result(self, output_data, action_name, expected_allowed, expected_addresses):
        action_results = output_data["action_results"]
        assert action_name in action_results

        result = action_results[action_name]
        assert result["allowed"] is expected_allowed
        assert result["addresses"] == expected_addresses
