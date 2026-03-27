from opssuite.templates.route_template import parse_route_template


def test_parse_route_template():
    parts = parse_route_template("/site/{region}/{rack}")
    assert "region" in parts
