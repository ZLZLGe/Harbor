import hashlib
import json
import os
from pathlib import Path


ROOT = Path(os.environ.get("CONTENT_ROOT", "/root"))


def _sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_protected_inputs_are_unchanged():
    expected = {
        str(ROOT / "launch_brief.md"): "282a8fbfc56476279bf9f17255b10b89a6ba5d79ec7ddd5410cce045ef360edc",
        str(ROOT / "channel_requirements.md"): "b40587905999c0c36f4cd7872f9b35633351d63b8305de1ea6d13c71ae094895",
        str(ROOT / "voice_guide.md"): "1b09ba832a142d9a670046905f6b3fd911a191c6fb85289998617e88252b76ef",
        str(ROOT / "build_bundle.py"): "cb09ea4a3fe43bf4b4333b6714e54d180771be39528dcbfc3c9874daa1cb89f6",
        str(ROOT / "fact_sheet.json"): "d0144d98f38fe73b51abf3283dd30f30de73e138da94092bedf8e5b2ce2e62e0",
        str(ROOT / "keyword_plan.json"): "5f593a1a3173e5a1d652467db764f958cbf6fc877a912b889b3c41b4747e6519",
        str(ROOT / "source_notes.md"): "c9afd148ba91337ffc42ac6f9d16afd6949a20e3b8d13e9ea9a5e4d1f9d86223",
    }

    for path, checksum in expected.items():
        assert _sha256(path) == checksum, f"Protected input changed: {path}"


def test_required_deliverables_are_present_and_nontrivial():
    assert (ROOT / "blog_post.md").exists()
    assert (ROOT / "linkedin_post.md").exists()
    assert (ROOT / "newsletter.json").exists()
    assert (ROOT / "seo_meta.json").exists()

    assert len((ROOT / "blog_post.md").read_text(encoding="utf-8").split()) >= 120
    assert len((ROOT / "linkedin_post.md").read_text(encoding="utf-8").split()) >= 50

    newsletter = json.loads((ROOT / "newsletter.json").read_text(encoding="utf-8"))
    seo_meta = json.loads((ROOT / "seo_meta.json").read_text(encoding="utf-8"))
    assert newsletter["subject"].strip()
    assert newsletter["body_markdown"].strip()
    assert seo_meta["title"].strip()
    assert seo_meta["description"].strip()
