from __future__ import annotations

import json
import hashlib
import os
import re
from pathlib import Path

WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
EXTENSION_ROOT = WORKSPACE_ROOT / "extension"
INPUT_HASH_RECORD = Path(os.environ.get("INPUT_HASH_RECORD", "/opt/release-briefing-inputs.sha256"))


def sha256_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def test_input_hashes_match_build_record() -> None:
    expected = {}
    for line in INPUT_HASH_RECORD.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, file_path = line.split(maxsplit=1)
        expected[file_path] = digest

    for file_path, digest in expected.items():
        actual = sha256_bytes(Path(file_path))
        assert actual == digest, f"input file changed: {file_path}"


def test_locale_files_cover_required_manifest_keys() -> None:
    manifest = json.loads((EXTENSION_ROOT / "package.json").read_text(encoding="utf-8"))
    token_keys = set()

    def walk(value):
        if isinstance(value, str):
            token_keys.update(token[1:-1] for token in re.findall(r"%[^%]+%", value))
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)

    walk(manifest)
    assert "walkthrough.step.browse.markdown" in token_keys
    assert "walkthrough.step.export.markdown" in token_keys

    for locale_file in [
        EXTENSION_ROOT / "package.nls.json",
        EXTENSION_ROOT / "package.nls.pt-br.json",
        EXTENSION_ROOT / "package.nls.zh-cn.json",
    ]:
        payload = json.loads(locale_file.read_text(encoding="utf-8"))
        for key in token_keys:
            assert key in payload and payload[key], f"missing key {key} in {locale_file.name}"


def test_runtime_bundles_share_the_same_keyset() -> None:
    extension_source = (EXTENSION_ROOT / "src" / "extension.js").read_text(encoding="utf-8")
    core_source = (EXTENSION_ROOT / "src" / "core.js").read_text(encoding="utf-8")
    english = json.loads((EXTENSION_ROOT / "l10n" / "bundle.l10n.json").read_text(encoding="utf-8"))
    pt = json.loads((EXTENSION_ROOT / "l10n" / "bundle.l10n.pt-br.json").read_text(encoding="utf-8"))
    zh = json.loads((EXTENSION_ROOT / "l10n" / "bundle.l10n.zh-cn.json").read_text(encoding="utf-8"))

    expected_keys = set(english)
    runtime_keys = set(re.findall(r'vscode\.l10n\.t\(\s*"([^"]+)"', extension_source))
    runtime_keys.update(re.findall(r'bundle\["([^"]+)"\]', core_source))

    missing = sorted(runtime_keys - expected_keys)
    assert not missing, f"english runtime bundle is missing referenced keys: {missing}"
    assert set(pt) == expected_keys, "pt-br runtime bundle keys differ from english bundle"
    assert set(zh) == expected_keys, "zh-cn runtime bundle keys differ from english bundle"
