import json
import os
import subprocess
import unittest
from pathlib import Path


WORKSPACE = Path(os.getenv("WORKSPACE", "/root"))
APP_DIR = Path(os.getenv("APP_DIR", str(WORKSPACE / "plugin-manifest-importer")))
PATCHES_DIR = Path(os.getenv("PATCHES_DIR", str(WORKSPACE / "patches")))
MANIFEST_DIR = Path(os.getenv("MANIFEST_DIR", str(WORKSPACE / "manifests")))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(WORKSPACE / "import-output")))
RUNTIME_ARTIFACTS_DIR = Path(os.getenv("RUNTIME_ARTIFACTS_DIR", str(WORKSPACE / "runtime-artifacts")))
JAR_PATH = APP_DIR / "target" / "plugin-manifest-importer.jar"
MARKER_PATH = RUNTIME_ARTIFACTS_DIR / "unexpected-step.txt"


def run_import(manifest_path: Path, output_name: str):
  output_path = OUTPUT_DIR / output_name
  result = subprocess.run(
      ["java", "-jar", str(JAR_PATH), "import", str(manifest_path), str(output_path)],
      cwd=APP_DIR,
      capture_output=True,
      text=True,
      timeout=20,
  )
  return result, output_path


class PluginManifestSecurityTests(unittest.TestCase):
  def test_patch_file_exists(self):
    self.assertTrue(PATCHES_DIR.exists(), "patches directory not found")

    patch_files = list(PATCHES_DIR.glob("*.patch"))
    self.assertTrue(patch_files, "expected at least one patch file")

    patch_text = "\n".join(path.read_text() for path in patch_files)
    self.assertIn("ManifestStep.java", patch_text)

  def test_repository_was_modified(self):
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
        timeout=10,
    )

    modified_files = [line for line in result.stdout.splitlines() if line.strip()]
    self.assertTrue(modified_files, "expected patched importer sources to differ from HEAD")

  def test_safe_manifest_import_still_works(self):
    result, output_path = run_import(MANIFEST_DIR / "safe-manifest.json", "safe-report.json")
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertTrue(output_path.exists(), "expected import output file to be created")

    report = json.loads(output_path.read_text())
    self.assertEqual(report["pluginId"], "analytics-exporter")
    self.assertEqual(report["importedStepCount"], 3)
    self.assertEqual(
        [step["kind"] for step in report["steps"]],
        ["copyAsset", "renderTemplate", "registerWebhook"],
    )
    self.assertIn("sample text only", report["notes"])

  def test_string_literal_mentions_do_not_trigger_rejection(self):
    result, output_path = run_import(MANIFEST_DIR / "string-literal-manifest.json", "string-literal-report.json")
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertTrue(output_path.exists(), "expected string-literal manifest to import successfully")

    report = json.loads(output_path.read_text())
    self.assertEqual(report["pluginId"], "docs-preview")
    self.assertIn("@type", report["notes"])
    self.assertEqual(report["steps"][0]["kind"], "copyAsset")

  def test_exploit_manifest_is_rejected_and_no_marker_is_written(self):
    result, output_path = run_import(MANIFEST_DIR / "exploit-manifest.json", "exploit-report.json")
    self.assertNotEqual(result.returncode, 0, "exploit manifest should be rejected")
    self.assertFalse(output_path.exists(), "rejected manifest must not produce an output file")
    self.assertFalse(MARKER_PATH.exists(), "dangerous internal step should never materialize")
    self.assertTrue(result.stderr.strip(), "rejection should provide an error message")

  def test_type_alias_hint_is_rejected(self):
    raw_manifest = """
{
  "pluginId": "alias-attempt",
  "version": "1.0.0",
  "owner": "third-party-upload",
  "notes": "trying an alternate type hint field",
  "steps": [
    {
      "type": "copyAsset",
      "@type": "com.harbor.pluginmanifest.steps.InternalScriptStep",
      "source": "assets/config.yaml",
      "destination": "plugins/alias/config.yaml"
    }
  ]
}
"""
    manifest_path = Path("/tmp/alias-hint-manifest.json")
    manifest_path.write_text(raw_manifest)

    result, output_path = run_import(manifest_path, "alias-hint-report.json")
    self.assertNotEqual(result.returncode, 0, "alternate type hint should be rejected")
    self.assertFalse(output_path.exists(), "rejected alias manifest must not produce an output file")


if __name__ == "__main__":
  unittest.main(verbosity=2)
