from pathlib import Path


base = Path("/root/repos")
expected = {
    "recordframe": "recordframe.parser.parse_record_stream",
    "tokenmesh": "tokenmesh.messages.parse_mesh_packet",
    "yamlishconf": "yamlishconf.loader.load_document",
}

libraries = (base / "libraries.txt").read_text().strip().splitlines()
assert libraries == sorted(expected), libraries

for repo, target in expected.items():
    notes = (base / repo / "notes_for_testing.txt").read_text()
    assert target in notes
    assert "risk summary:" in notes
    assert "test oracle hint:" in notes
