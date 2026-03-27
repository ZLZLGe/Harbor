from slugrender.template import load_template_bundle, parse_slug_template


def test_parse_slug_template():
    parts = parse_slug_template("region-{site}-{date}")
    assert parts[0] == "region-"


def test_load_template_bundle():
    bundle = load_template_bundle('{"templates": [{"name": "site", "template": "region-{site}"}]}')
    assert bundle["site"] == "region-{site}"
