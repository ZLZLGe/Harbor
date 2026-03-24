#!/bin/bash
set -euo pipefail

cat > archive_fuzz_targets.md <<'EOF'
# archive fuzz targets

## Important Files

- `archivekit/headers.py`
  - `parse_header_block` is the first structured boundary for every 512-byte header block.
  - `_parse_numeric_field` accepts both octal and base-256 encodings, so malformed numeric fields can reach unusual parsing paths.
  - A checksum mismatch already raises, which gives a clear oracle for future robustness tests.
- `archivekit/metadata.py`
  - `parse_extended_headers` walks attacker-controlled length-prefixed records and performs UTF-8 decoding on both keys and values.
  - The parser is stateful across offsets, so truncated or inconsistent record lengths are high-value edge cases.
- `archivekit/reader.py`
  - `ArchiveReader.iter_entries` coordinates block reads, header parsing, metadata carry-over, payload reads, and padding skips.
  - It is the highest-level entry point that composes the lower-level parsers and can expose cross-record state bugs.
- `archivekit/stream.py`
  - `BlockStream.read_block`, `read_exact`, and `skip_padding` define EOF behavior for truncated archives.
  - These paths are only lightly covered through happy-path reader tests.
- `archivekit/filters.py`
  - `decode_member_path` and `sanitize_destination` touch path normalization and extraction safety.
  - The current tests only check a very small set of path forms.

## Important Functions

- `archivekit.headers.parse_header_block`
  - Input surface: raw 512-byte header blocks from untrusted archives.
  - Risk: checksum verification, prefix handling, and multiple numeric subfields all happen in one place.
  - Existing coverage: `tests/test_headers.py` only checks one valid block.
  - Harnessability: high, because a single block is enough to drive the parser.
- `archivekit.headers._parse_numeric_field`
  - Input surface: short fixed-width byte slices with octal or base-256 values.
  - Risk: malformed octal digits, sign handling, empty fields, and overlarge encodings can all change control flow.
  - Existing coverage: one base-256 happy path in `tests/test_headers.py`.
  - Harnessability: high, because inputs are tiny and the expected exception behavior is observable.
- `archivekit.metadata.parse_extended_headers`
  - Input surface: arbitrary length-prefixed records with UTF-8 decoding.
  - Risk: inconsistent record lengths, missing separators, missing trailing newline, duplicate keys, and invalid Unicode.
  - Existing coverage: only exercised indirectly through `tests/test_reader.py`.
  - Harnessability: high, because a byte string is sufficient.
- `archivekit.reader.ArchiveReader.iter_entries`
  - Input surface: complete archive streams with interacting headers, payloads, and padding.
  - Risk: state carry-over from PAX headers, truncated payloads, and ordering bugs between metadata and file entries.
  - Existing coverage: one archive with one PAX record and one regular file in `tests/test_reader.py`.
  - Harnessability: medium, because the seed should preserve basic archive framing.
- `archivekit.filters.decode_member_path`
  - Input surface: raw path bytes that may contain null padding or undecodable sequences.
  - Risk: normalization differences and surrogate escapes can produce surprising path strings.
  - Existing coverage: one normal null-padded path in `tests/test_filters.py`.
  - Harnessability: high, because the function takes a single byte string.

## Existing Tests And Gaps

- `tests/test_headers.py` confirms that a valid header parses and that one base-256 field decodes correctly.
- `tests/test_reader.py` confirms that a single PAX header is carried into the next file entry.
- `tests/test_filters.py` checks one null-padded path and one parent-traversal rejection.

The main gaps are:

- No test for truncated header blocks, truncated payloads, or short padding reads, so EOF behavior in `archivekit.stream` and `ArchiveReader.iter_entries` is largely untested.
- No negative tests for checksum mismatch, invalid octal digits, empty numeric fields, or more unusual base-256 encodings in `_parse_numeric_field`.
- No direct tests for malformed PAX record lengths, missing `=` separators, missing trailing newline, or invalid UTF-8 in `parse_extended_headers`.
- No coverage for non-UTF-8 filenames, repeated path segments, or path normalization corner cases in `decode_member_path`.

## Final Shortlist

1. `archivekit.headers.parse_header_block`
   - Highest priority because every archive entry passes through it and it combines checksum logic with multiple numeric decoders.
   - Missing coverage includes checksum mismatch, malformed size fields, empty numeric slices, and unusual prefix/name combinations.
   - Good seed ideas: a valid single header block, a header with one flipped checksum byte, and blocks that swap octal fields for base-256 encodings.

2. `archivekit.metadata.parse_extended_headers`
   - Highest-value metadata parser because it consumes attacker-controlled length prefixes and UTF-8 text.
   - Missing coverage includes truncated records, bad length declarations, missing newline terminators, and invalid Unicode in keys or values.
   - Good seed ideas: one valid `path=` record, one record with mismatched declared length, and one record with non-UTF-8 bytes after the `=` separator.

3. `archivekit.reader.ArchiveReader.iter_entries`
   - Best end-to-end target because it composes block framing, header parsing, PAX carry-over, payload reads, and padding.
   - Missing coverage includes truncated archives, multiple consecutive metadata records, zero-sized entries mixed with normal files, and state reset bugs after malformed metadata.
   - Good seed ideas: a one-file archive, a PAX-plus-file archive, and an archive that ends mid-payload or mid-padding block.
EOF
