from graphbundle.bundle import parse_bundle


def test_parse_bundle_counts_nodes():
    document = parse_bundle("n1:alpha\nn2:beta")
    assert document["count"] == 2
