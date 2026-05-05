from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
EXTENSION_ROOT = WORKSPACE_ROOT / "extension"
OUTPUT_ROOT = WORKSPACE_ROOT / "output"
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/app/data"))
TESTS_ROOT = Path(os.environ.get("TESTS_ROOT", "/tests"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_default_outputs_exist() -> None:
    expected = [
        OUTPUT_ROOT / "release-briefing.en.md",
        OUTPUT_ROOT / "release-briefing.pt-br.md",
        OUTPUT_ROOT / "release-briefing.zh-cn.md",
        OUTPUT_ROOT / "release-briefing-extension.vsix",
    ]
    missing = [str(path) for path in expected if not path.exists()]
    assert not missing, f"missing output artifacts: {missing}"


def test_markdown_outputs_are_localized() -> None:
    en = read_text(OUTPUT_ROOT / "release-briefing.en.md")
    pt = read_text(OUTPUT_ROOT / "release-briefing.pt-br.md")
    zh = read_text(OUTPUT_ROOT / "release-briefing.zh-cn.md")

    assert "# VS Code Release Briefing" in en
    assert "## Overview" in en and "## Highlights" in en and "## Action items" in en
    assert "Local workspace extensions preview" in en
    assert "Generated with" in en
    assert "Release Briefing Explorer" in en

    assert "# Resumo de Atualizações do VS Code" in pt
    assert "## Visão geral" in pt and "## Destaques" in pt and "## Ações" in pt
    assert "Prévia de extensões locais de workspace" in pt
    assert "Release Briefing Explorer" in pt or "Explorador de Resumos" in pt or "Gerado com" in pt

    assert "# VS Code 更新简报" in zh
    assert "## 概览" in zh and "## 重点" in zh and "## 行动项" in zh
    assert "本地工作区扩展预览" in zh
    assert (
        "生成工具" in zh
        or "由 Release Briefing Explorer 生成" in zh
        or "由版本简报浏览器生成" in zh
        or "由版本简报资源管理器生成" in zh
        or "发布简报浏览器" in zh
    )
    assert (
        "Release Briefing Explorer" in zh
        or "更新简报浏览器" in zh
        or "版本简报浏览器" in zh
        or "版本简报资源管理器" in zh
        or "发布简报浏览器" in zh
    )


def test_manifest_uses_tokenized_localization_surfaces() -> None:
    manifest = json.loads((EXTENSION_ROOT / "package.json").read_text(encoding="utf-8"))

    assert manifest["displayName"].startswith("%")
    assert manifest["description"].startswith("%")
    assert manifest["contributes"]["commands"][0]["title"].startswith("%")
    assert manifest["contributes"]["viewsContainers"]["activitybar"][0]["title"].startswith("%")
    assert manifest["contributes"]["views"]["releaseBriefing"][0]["name"].startswith("%")
    assert manifest["contributes"]["walkthroughs"][0]["steps"][0]["media"]["markdown"].startswith("%")
    assert manifest["contributes"]["walkthroughs"][0]["steps"][1]["media"]["markdown"].startswith("%")


def test_packaged_vsix_contains_localization_assets() -> None:
    vsix_path = OUTPUT_ROOT / "release-briefing-extension.vsix"
    with zipfile.ZipFile(vsix_path) as archive:
        members = set(archive.namelist())

    required = {
        "extension/package.nls.json",
        "extension/package.nls.pt-br.json",
        "extension/package.nls.zh-cn.json",
        "extension/l10n/bundle.l10n.json",
        "extension/l10n/bundle.l10n.pt-br.json",
        "extension/l10n/bundle.l10n.zh-cn.json",
        "extension/resources/walkthrough/pt-br/browse.md",
        "extension/resources/walkthrough/pt-br/export.md",
        "extension/resources/walkthrough/zh-cn/browse.md",
        "extension/resources/walkthrough/zh-cn/export.md",
    }
    missing = sorted(required - members)
    assert not missing, f"vsix is missing localized assets: {missing}"


def test_variant_request_changes_selected_content() -> None:
    variant_request = TESTS_ROOT / "fixtures" / "briefing_request_variant.json"
    with tempfile.TemporaryDirectory() as temp_dir:
        env = os.environ.copy()
        env["RELEASE_BRIEFING_DATA_ROOT"] = DATA_ROOT.as_posix()
        env["RELEASE_BRIEFING_OUTPUT_ROOT"] = temp_dir
        node_script = f"""
const path = require("path");
const {{ buildBriefings }} = require("{(EXTENSION_ROOT / 'src' / 'core.js').as_posix()}");
buildBriefings({{
  extensionRoot: "{EXTENSION_ROOT.as_posix()}",
  dataRoot: "{DATA_ROOT.as_posix()}",
  outputRoot: "{Path(temp_dir).as_posix()}",
  requestPath: "{variant_request.as_posix()}"
}});
"""
        subprocess.run(["node", "-e", node_script], check=True, env=env, cwd=EXTENSION_ROOT)
        variant_en = Path(temp_dir) / "release-briefing.en.md"
        content = read_text(variant_en)

    assert "VS Code Workspace Extension Briefing" in content
    assert "VS Code 1.87" not in content
    assert "Webview and custom editor support for floating windows" in content
    assert "Accessibility help for extension-contributed views" in content
    assert "Language model access control for extensions" not in content


def test_locale_term_assets_drive_localized_outputs() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        variant_root = Path(temp_dir) / "data"
        shutil.copytree(DATA_ROOT, variant_root)

        pt_terms_path = variant_root / "locales" / "pt-br" / "briefing_terms.json"
        zh_terms_path = variant_root / "locales" / "zh-cn" / "briefing_terms.json"

        pt_terms = json.loads(pt_terms_path.read_text(encoding="utf-8"))
        zh_terms = json.loads(zh_terms_path.read_text(encoding="utf-8"))

        pt_terms["headings"]["overview"] = "Visao geral de validacao"
        pt_terms["focus_names"]["views"] = "Views em validacao"

        zh_terms["headings"]["overview"] = "概览校验项"
        zh_terms["focus_names"]["views"] = "视图校验项"

        pt_terms_path.write_text(json.dumps(pt_terms, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        zh_terms_path.write_text(json.dumps(zh_terms, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        output_root = Path(temp_dir) / "output"
        env = os.environ.copy()
        env["RELEASE_BRIEFING_DATA_ROOT"] = variant_root.as_posix()
        env["RELEASE_BRIEFING_OUTPUT_ROOT"] = output_root.as_posix()
        node_script = f"""
const {{ buildBriefings }} = require("{(EXTENSION_ROOT / 'src' / 'core.js').as_posix()}");
buildBriefings({{
  extensionRoot: "{EXTENSION_ROOT.as_posix()}",
  dataRoot: "{variant_root.as_posix()}",
  outputRoot: "{output_root.as_posix()}"
}});
"""
        subprocess.run(["node", "-e", node_script], check=True, env=env, cwd=EXTENSION_ROOT)

        pt_output = read_text(output_root / "release-briefing.pt-br.md")
        zh_output = read_text(output_root / "release-briefing.zh-cn.md")
        en_output = read_text(output_root / "release-briefing.en.md")

    assert "Visao geral de validacao" in pt_output
    assert "Views em validacao" in pt_output

    assert "概览校验项" in zh_output
    assert "视图校验项" in zh_output

    assert "Visao geral de validacao" not in en_output
    assert "概览校验项" not in en_output


def test_release_note_renderer_respects_injected_locale_assets() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        variant_root = Path(temp_dir) / "data"
        variant_extension_root = Path(temp_dir) / "extension"
        shutil.copytree(DATA_ROOT, variant_root)
        shutil.copytree(EXTENSION_ROOT, variant_extension_root)

        pt_terms_path = variant_root / "locales" / "pt-br" / "briefing_terms.json"
        zh_terms_path = variant_root / "locales" / "zh-cn" / "briefing_terms.json"
        pt_bundle_path = variant_extension_root / "l10n" / "bundle.l10n.pt-br.json"
        zh_bundle_path = variant_extension_root / "l10n" / "bundle.l10n.zh-cn.json"

        pt_terms = json.loads(pt_terms_path.read_text(encoding="utf-8"))
        zh_terms = json.loads(zh_terms_path.read_text(encoding="utf-8"))
        pt_bundle = json.loads(pt_bundle_path.read_text(encoding="utf-8"))
        zh_bundle = json.loads(zh_bundle_path.read_text(encoding="utf-8"))

        pt_terms["focus_names"]["views"] = "Views em revisao"
        zh_terms["focus_names"]["views"] = "视图复核项"
        pt_bundle["Highlights in briefing scope"] = "Destaques validados"
        zh_bundle["Highlights in briefing scope"] = "范围内重点校验"
        pt_bundle["Focus: {0}"] = "Area validada: {0}"
        zh_bundle["Focus: {0}"] = "校验范围：{0}"
        pt_terms_path.write_text(json.dumps(pt_terms, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        zh_terms_path.write_text(json.dumps(zh_terms, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        pt_bundle_path.write_text(json.dumps(pt_bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        zh_bundle_path.write_text(json.dumps(zh_bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        env = os.environ.copy()
        env["RELEASE_BRIEFING_DATA_ROOT"] = DATA_ROOT.as_posix()
        node_script = f"""
const core = require("{(EXTENSION_ROOT / 'src' / 'core.js').as_posix()}");
const pt = core.renderReleaseNote(
  "1.88",
  "pt-BR",
  "{variant_root.as_posix()}",
  "{variant_extension_root.as_posix()}"
);
const zh = core.renderReleaseNote(
  "1.89",
  "zh-CN",
  "{variant_root.as_posix()}",
  "{variant_extension_root.as_posix()}"
);
console.log("===PT===");
console.log(pt);
console.log("===ZH===");
console.log(zh);
"""
        rendered = subprocess.run(
            ["node", "-e", node_script],
            check=True,
            env=env,
            cwd=EXTENSION_ROOT,
            capture_output=True,
            text=True,
        ).stdout

    pt_output = rendered.split("===PT===\n", 1)[1].split("\n===ZH===\n", 1)[0]
    zh_output = rendered.split("\n===ZH===\n", 1)[1]

    assert "Views em revisao" in pt_output
    assert "视图复核项" in zh_output


def test_export_footer_uses_injected_bundle_assets() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        variant_root = Path(temp_dir) / "data"
        variant_extension_root = Path(temp_dir) / "extension"
        shutil.copytree(DATA_ROOT, variant_root)
        shutil.copytree(EXTENSION_ROOT, variant_extension_root)

        pt_bundle_path = variant_extension_root / "l10n" / "bundle.l10n.pt-br.json"
        zh_bundle_path = variant_extension_root / "l10n" / "bundle.l10n.zh-cn.json"

        pt_bundle = json.loads(pt_bundle_path.read_text(encoding="utf-8"))
        zh_bundle = json.loads(zh_bundle_path.read_text(encoding="utf-8"))
        pt_bundle["Release Briefing Explorer"] = "Explorador de Resumos"
        zh_bundle["Release Briefing Explorer"] = "版本简报浏览器"
        pt_bundle_path.write_text(json.dumps(pt_bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        zh_bundle_path.write_text(json.dumps(zh_bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        output_root = Path(temp_dir) / "output"
        env = os.environ.copy()
        env["RELEASE_BRIEFING_DATA_ROOT"] = variant_root.as_posix()
        env["RELEASE_BRIEFING_OUTPUT_ROOT"] = output_root.as_posix()
        node_script = f"""
const {{ buildBriefings }} = require("{(EXTENSION_ROOT / 'src' / 'core.js').as_posix()}");
buildBriefings({{
  extensionRoot: "{variant_extension_root.as_posix()}",
  dataRoot: "{variant_root.as_posix()}",
  outputRoot: "{output_root.as_posix()}"
}});
"""
        subprocess.run(
            ["node", "-e", node_script],
            check=True,
            env=env,
            cwd=EXTENSION_ROOT,
        )

        pt_output = read_text(output_root / "release-briefing.pt-br.md")
        zh_output = read_text(output_root / "release-briefing.zh-cn.md")

    assert "Explorador de Resumos" in pt_output
    assert "版本简报浏览器" in zh_output


def test_release_note_renderer_separates_out_of_scope_highlights() -> None:
    env = os.environ.copy()
    env["RELEASE_BRIEFING_DATA_ROOT"] = DATA_ROOT.as_posix()
    node_script = f"""
const core = require("{(EXTENSION_ROOT / 'src' / 'core.js').as_posix()}");
const rendered = core.renderReleaseNote(
  "1.87",
  "en",
  "{DATA_ROOT.as_posix()}",
  "{EXTENSION_ROOT.as_posix()}"
);
console.log(rendered);
"""
    rendered = subprocess.run(
        ["node", "-e", node_script],
        check=True,
        env=env,
        cwd=EXTENSION_ROOT,
        capture_output=True,
        text=True,
    ).stdout

    in_scope_title = "FindFiles2 proposal for richer file queries"
    out_of_scope_title = "Test coverage support for extension test runs"
    assert in_scope_title in rendered
    assert out_of_scope_title in rendered
