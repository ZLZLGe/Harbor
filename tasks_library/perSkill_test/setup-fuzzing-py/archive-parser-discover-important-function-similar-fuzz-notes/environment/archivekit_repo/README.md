# archivekit

`archivekit` is a small reference project that reads TAR-like archive streams.
It focuses on three boundaries that are relevant for robustness work:

- fixed-width header decoding
- PAX-style extended metadata parsing
- streaming iteration over archive entries

The code intentionally has a compact public API:

- `archivekit.headers.parse_header_block`
- `archivekit.metadata.parse_extended_headers`
- `archivekit.reader.ArchiveReader.iter_entries`
- `archivekit.filters.decode_member_path`

The existing tests mostly exercise happy-path archives and a few normal decoding cases.
They do not try malformed lengths, truncated streams, or unusual numeric encodings exhaustively.
