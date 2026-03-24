import json
import os
import unittest
import urllib.error
import urllib.request
from pathlib import Path


WORKSPACE = Path(os.getenv("WORKSPACE", "/root"))
SERVICE_DIR = Path(os.getenv("SERVICE_DIR", str(WORKSPACE / "preview-service")))
PREVIEW_HOST = os.getenv("PREVIEW_HOST", "localhost")
PREVIEW_PORT = int(os.getenv("PREVIEW_PORT", "8080"))
BASE_URL = f"http://{PREVIEW_HOST}:{PREVIEW_PORT}"


def post_preview(payload=None, raw_body=None):
  if raw_body is None:
    raw_body = json.dumps(payload)

  request = urllib.request.Request(
      f"{BASE_URL}/api/v1/preview",
      data=raw_body.encode("utf-8"),
      headers={"Content-Type": "application/json"},
      method="POST",
  )

  try:
    with urllib.request.urlopen(request, timeout=5) as response:
      return response.status, response.read().decode("utf-8")
  except urllib.error.HTTPError as exc:
    return exc.code, exc.read().decode("utf-8")


class PreviewSecurityTests(unittest.TestCase):
  def test_patch_file_exists(self):
    patches_dir = WORKSPACE / "patches"
    self.assertTrue(patches_dir.exists(), "patches directory not found")

    patch_files = list(patches_dir.glob("*.patch"))
    self.assertTrue(patch_files, "expected at least one patch file")

    patch_text = "\n".join(path.read_text() for path in patch_files)
    self.assertIn("PreviewHandler.java", patch_text)

  def test_legitimate_projection_still_works(self):
    payload = {
        "source": {
            "rows": [
                {"city": "Hong Kong", "visits": 8},
                {"city": "Singapore", "visits": 5},
            ]
        },
        "transform": {
            "mode": "select",
            "field": "city",
        },
    }

    status, body = post_preview(payload=payload)
    self.assertEqual(status, 200, body)

    response = json.loads(body)
    self.assertFalse(response["scriptApplied"])
    self.assertEqual(response["rowCount"], 2)
    self.assertEqual([row["city"] for row in response["rows"]], ["Hong Kong", "Singapore"])

  def test_script_mode_without_override_stays_blocked(self):
    payload = {
        "source": {
            "rows": [
                {"city": "Hong Kong", "visits": 8},
            ]
        },
        "transform": {
            "mode": "script",
            "field": "city",
            "expression": "city + '-preview'",
        },
    }

    status, body = post_preview(payload=payload)
    self.assertEqual(status, 400, body)
    self.assertIn("disabled", body.lower())

  def test_empty_key_bypass_is_rejected(self):
    payload = {
        "source": {
            "rows": [
                {"city": "Hong Kong", "visits": 8},
            ]
        },
        "transform": {
            "mode": "script",
            "field": "city",
            "expression": "city + '-preview'",
            "": {"enabled": True},
        },
    }

    status, body = post_preview(raw_body=json.dumps(payload, indent=2))
    self.assertEqual(status, 400, body)
    self.assertIn("empty", body.lower())

  def test_string_literal_that_mentions_attack_text_is_allowed(self):
    payload = {
        "source": {
            "rows": [
                {
                    "note": "Reviewer pasted the sample text \"\": {\"enabled\": true} into a comment.",
                    "city": "Hong Kong",
                }
            ]
        },
        "transform": {
            "mode": "select",
            "field": "note",
        },
    }

    status, body = post_preview(payload=payload)
    self.assertEqual(status, 200, body)

    response = json.loads(body)
    self.assertEqual(response["rows"][0]["note"], payload["source"]["rows"][0]["note"])


if __name__ == "__main__":
  unittest.main(verbosity=2)
