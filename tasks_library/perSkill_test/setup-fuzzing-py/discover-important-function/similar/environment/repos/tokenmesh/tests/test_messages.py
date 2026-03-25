from tokenmesh.messages import parse_mesh_packet


def test_parse_mesh_packet_requires_payload():
    try:
        parse_mesh_packet("HEAD")
    except ValueError as exc:
        assert "not enough" in str(exc)
    else:
        raise AssertionError("expected ValueError")
