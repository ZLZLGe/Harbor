from opssuite.export.archive_index import load_archive_index


def test_load_archive_index():
    rows = load_archive_index("path,size\nlogs/a.txt,12\n")
    assert rows[0]["path"] == "logs/a.txt"
