You need to create a Python fuzz driver for the repo at `/root/quota_lang`.

The repo already includes a local fuzz runtime shim in its root directory.
Inspect the repo, write `/root/quota_lang/fuzz.py`, and quick-run it so that `/root/quota_lang/fuzz.log` is created.

The driver should exercise the repo's main parser boundary and ignore expected parse failures instead of crashing.
