from pathlib import Path


OUTPUT_PATH = Path("/root/transfer3_digest_fingerprints.tsv")

EXPECTED = """frame_number\tlane\tbatch\trecords\tsha256_prefix
16\teast\tA-07\t23\tabcdefabcdef
28\teast\tA-09\t7\t123451234512
4\twest\tB-01\t18\t111111111111
"""


def test_expected_tsv():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"
    assert OUTPUT_PATH.read_text() == EXPECTED


def main() -> None:
    test_expected_tsv()
    print("transfer3 verifier checks passed")


if __name__ == "__main__":
    main()
