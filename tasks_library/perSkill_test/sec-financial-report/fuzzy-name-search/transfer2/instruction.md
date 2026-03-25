The issuer watchlist at `/root/data/issuer_watchlist.json` contains approximate company names from a trading note.

Resolve each alias to the best matching issuer name and CUSIP, keeping the same order as the input list, and write `/root/issuer_resolution.json`.

The file must be a JSON array of objects with this exact schema:

```json
[
  {
    "alias": "string",
    "issuer_name": "string",
    "cusip": "string"
  }
]
```
