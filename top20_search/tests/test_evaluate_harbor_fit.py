import json
import os
import tempfile
import unittest
import requests
from unittest import mock

from top20_search.src import evaluate_harbor_fit
from top20_search.src import openai_review_client


def make_fake_bucket_rules(*, enabled=True, max_markdown_files=2, max_total_characters=500):
    return {
        "_shared": {
            "enabled": enabled,
            "summary": "shared harbor rubric",
            "keep_rules": [
                {"id": "bucket_fit", "text": "fit", "required": True},
                {"id": "concrete_artifacts", "text": "artifacts", "required": True},
                {"id": "self_contained_context", "text": "context", "required": True},
                {"id": "reproducible_environment", "text": "repro", "required": True},
                {"id": "verifier_ready", "text": "verifier", "required": True},
            ],
            "drop_rules": [
                {"id": "meta_only", "text": "meta"},
                {"id": "external_dependency_heavy", "text": "external"},
            ],
            "preferred_model": "gpt-5.4-mini",
            "max_markdown_files": max_markdown_files,
            "max_total_characters": max_total_characters,
        }
    }


class EvaluateHarborFitTests(unittest.TestCase):
    def test_load_bucket_review_rules_accepts_shared_only_config(self):
        shared_only_config = """
bucket_review_rules:
  _shared:
    enabled: true
    summary: shared harbor rubric
    keep_rules:
      - id: bucket_fit
        text: fit
        required: true
    drop_rules:
      - id: meta_only
        text: meta
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "bucket_review_rules.yaml")
            with open(config_path, "w", encoding="utf-8") as stream:
                stream.write(shared_only_config)

            rules = evaluate_harbor_fit.load_bucket_review_rules(config_path)

        self.assertEqual(set(rules), {"_shared"})
        self.assertTrue(rules["_shared"]["enabled"])
        self.assertEqual(rules["_shared"]["keep_rules"][0]["id"], "bucket_fit")

    def test_load_data_quality_review_rules(self):
        rules = evaluate_harbor_fit.load_bucket_review_rules()
        self.assertEqual(set(rules), {"_shared"})
        self.assertTrue(rules["_shared"]["enabled"])
        self.assertEqual(rules["_shared"]["keep_rules"][0]["id"], "bucket_fit")
        self.assertTrue(rules["_shared"]["keep_rules"][0]["required"])

    def test_parse_openai_review_output(self):
        payload = {
            "selected": True,
            "decision": "keep",
            "summary": "This skill defines repeatable data-quality checks.",
            "matched_keep_rules": ["Provides explicit validation checks"],
            "matched_drop_rules": [],
            "confidence": "high",
        }
        parsed = evaluate_harbor_fit.parse_review_payload(payload, model_name="gpt-5.4-mini")
        self.assertTrue(parsed["selected"])
        self.assertEqual(parsed["decision"], "keep")
        self.assertEqual(parsed["model"], "gpt-5.4-mini")

    def test_parse_openai_review_output_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            evaluate_harbor_fit.parse_review_payload({"selected": True}, model_name="gpt-5.4-mini")

    def test_parse_openai_review_output_rejects_non_bool_selected(self):
        payload = {
            "selected": "true",
            "decision": "keep",
            "summary": "summary",
            "matched_keep_rules": ["k1"],
            "matched_drop_rules": [],
            "confidence": "high",
        }
        with self.assertRaisesRegex(ValueError, "selected"):
            evaluate_harbor_fit.parse_review_payload(payload, model_name="gpt-5.4-mini")

    def test_parse_openai_review_output_rejects_invalid_confidence(self):
        payload = {
            "selected": True,
            "decision": "keep",
            "summary": "summary",
            "matched_keep_rules": ["k1"],
            "matched_drop_rules": [],
            "confidence": "certain",
        }
        with self.assertRaisesRegex(ValueError, "confidence"):
            evaluate_harbor_fit.parse_review_payload(payload, model_name="gpt-5.4-mini")

    def test_parse_openai_review_output_rejects_invalid_keep_rules_type(self):
        payload = {
            "selected": True,
            "decision": "keep",
            "summary": "summary",
            "matched_keep_rules": "k1",
            "matched_drop_rules": [],
            "confidence": "high",
        }
        with self.assertRaisesRegex(ValueError, "matched_keep_rules"):
            evaluate_harbor_fit.parse_review_payload(payload, model_name="gpt-5.4-mini")

    def test_load_bucket_review_rules_rejects_non_mapping_bucket_rule(self):
        bad_config = """
bucket_review_rules:
  _shared:
    enabled: true
    keep_rules:
      - id: bucket_fit
        text: fit
        required: true
    drop_rules:
      - id: meta_only
        text: meta
  data-quality: []
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "bucket_review_rules.yaml")
            with open(config_path, "w", encoding="utf-8") as stream:
                stream.write(bad_config)
            with self.assertRaisesRegex(ValueError, "data-quality"):
                evaluate_harbor_fit.load_bucket_review_rules(config_path)

    def test_evaluate_skill_bundle_uses_skill_md_first(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = os.path.join(tmpdir, "SKILL.md")
            readme_path = os.path.join(tmpdir, "README.md")
            notes_path = os.path.join(tmpdir, "docs.md")
            with open(skill_path, "w", encoding="utf-8") as stream:
                stream.write("skill content")
            with open(readme_path, "w", encoding="utf-8") as stream:
                stream.write("readme content")
            with open(notes_path, "w", encoding="utf-8") as stream:
                stream.write("notes content")

            fake_rules = {
                **make_fake_bucket_rules(max_markdown_files=2, max_total_characters=500)
            }
            captured: dict[str, str] = {}

            def fake_review_client(*, model, system_prompt, user_prompt):
                captured["model"] = model
                captured["system_prompt"] = system_prompt
                captured["user_prompt"] = user_prompt
                return {
                    "selected": True,
                    "decision": "keep",
                    "summary": "ok",
                    "matched_keep_rules": [
                        "bucket_fit",
                        "concrete_artifacts",
                        "self_contained_context",
                        "reproducible_environment",
                        "verifier_ready",
                    ],
                    "matched_drop_rules": [],
                    "confidence": "high",
                }

            with mock.patch.object(evaluate_harbor_fit, "load_bucket_review_rules", return_value=fake_rules):
                result = evaluate_harbor_fit.evaluate_skill_bundle(
                    tmpdir,
                    bucket_slug="data-quality",
                    review_client=fake_review_client,
                )

        self.assertTrue(result["selected"])
        self.assertEqual(captured["model"], "gpt-5.4-mini")
        self.assertIn("# FILE: SKILL.md", captured["user_prompt"])
        self.assertIn("# FILE: README.md", captured["user_prompt"])
        self.assertNotIn("# FILE: docs.md", captured["user_prompt"])
        self.assertLess(
            captured["user_prompt"].find("# FILE: SKILL.md"),
            captured["user_prompt"].find("# FILE: README.md"),
        )

    def test_evaluate_skill_bundle_rejects_disabled_bucket(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "SKILL.md"), "w", encoding="utf-8") as stream:
                stream.write("content")
            with self.assertRaisesRegex(ValueError, "not enabled"):
                with mock.patch.object(
                    evaluate_harbor_fit,
                    "load_bucket_review_rules",
                    return_value=make_fake_bucket_rules(enabled=False),
                ):
                    evaluate_harbor_fit.evaluate_skill_bundle(tmpdir, bucket_slug="xlsx")

    def test_evaluate_skill_bundle_includes_bundle_files_used(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "SKILL.md"), "w", encoding="utf-8") as stream:
                stream.write("skill content")
            with open(os.path.join(tmpdir, "README.md"), "w", encoding="utf-8") as stream:
                stream.write("readme content")

            fake_rules = make_fake_bucket_rules(max_markdown_files=2, max_total_characters=500)

            def fake_review_client(*, model, system_prompt, user_prompt):
                return {
                    "selected": True,
                    "decision": "keep",
                    "summary": "ok",
                    "matched_keep_rules": [
                        "bucket_fit",
                        "concrete_artifacts",
                        "self_contained_context",
                        "reproducible_environment",
                        "verifier_ready",
                    ],
                    "matched_drop_rules": [],
                    "confidence": "high",
                }

            with mock.patch.object(evaluate_harbor_fit, "load_bucket_review_rules", return_value=fake_rules):
                result = evaluate_harbor_fit.evaluate_skill_bundle(
                    tmpdir,
                    bucket_slug="data-quality",
                    review_client=fake_review_client,
                )

        self.assertEqual(result["bundle_files_used"], ["SKILL.md", "README.md"])

    def test_select_bundle_markdown_truncates_first_file_when_over_char_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "SKILL.md"), "w", encoding="utf-8") as stream:
                stream.write("x" * 100)

            files, text = evaluate_harbor_fit.select_bundle_markdown(
                tmpdir,
                max_files=3,
                max_total_characters=10,
            )

        self.assertEqual(files, ["SKILL.md"])
        self.assertIn("# FILE: SKILL.md", text)
        self.assertEqual(len(text.splitlines()[-1]), 10)

    def test_select_bundle_markdown_respects_zero_max_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "SKILL.md"), "w", encoding="utf-8") as stream:
                stream.write("skill content")
            with open(os.path.join(tmpdir, "README.md"), "w", encoding="utf-8") as stream:
                stream.write("readme content")

            files, text = evaluate_harbor_fit.select_bundle_markdown(
                tmpdir,
                max_files=0,
                max_total_characters=1000,
            )

        self.assertEqual(files, [])
        self.assertEqual(text, "")

    def test_evaluate_skill_bundle_defaults_bucket_slug_when_omitted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "SKILL.md"), "w", encoding="utf-8") as stream:
                stream.write("skill content")

            fake_rules = make_fake_bucket_rules(max_markdown_files=2, max_total_characters=500)
            captured: dict[str, str] = {}

            def fake_review_client(*, model, system_prompt, user_prompt):
                captured["user_prompt"] = user_prompt
                return {
                    "selected": True,
                    "decision": "keep",
                    "summary": "ok",
                    "matched_keep_rules": [
                        "bucket_fit",
                        "concrete_artifacts",
                        "self_contained_context",
                        "reproducible_environment",
                        "verifier_ready",
                    ],
                    "matched_drop_rules": [],
                    "confidence": "high",
                }

            with mock.patch.object(evaluate_harbor_fit, "load_bucket_review_rules", return_value=fake_rules):
                result = evaluate_harbor_fit.evaluate_skill_bundle(
                    tmpdir,
                    review_client=fake_review_client,
                )

        self.assertTrue(result["selected"])
        self.assertIn("Bucket: data-quality", captured["user_prompt"])

    def test_evaluate_skill_bundle_uses_shared_rules_for_any_bucket_slug(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "SKILL.md"), "w", encoding="utf-8") as stream:
                stream.write("skill content")

            captured: dict[str, str] = {}

            def fake_review_client(*, model, system_prompt, user_prompt):
                captured["user_prompt"] = user_prompt
                return {
                    "selected": True,
                    "decision": "keep",
                    "summary": "ok",
                    "matched_keep_rules": [
                        "bucket_fit",
                        "concrete_artifacts",
                        "self_contained_context",
                        "reproducible_environment",
                        "verifier_ready",
                    ],
                    "matched_drop_rules": [],
                    "confidence": "high",
                }

            with mock.patch.object(
                evaluate_harbor_fit,
                "load_bucket_review_rules",
                return_value=make_fake_bucket_rules(),
            ):
                result = evaluate_harbor_fit.evaluate_skill_bundle(
                    tmpdir,
                    bucket_slug="totally-new-bucket",
                    review_client=fake_review_client,
                )

        self.assertTrue(result["selected"])
        self.assertIn("Bucket: totally-new-bucket", captured["user_prompt"])

    def test_evaluate_skill_bundle_wraps_openai_review_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "SKILL.md"), "w", encoding="utf-8") as stream:
                stream.write("skill content")

            fake_rules = make_fake_bucket_rules(max_markdown_files=2, max_total_characters=500)

            def failing_review_client(*, model, system_prompt, user_prompt):
                raise openai_review_client.OpenAIReviewError("upstream failure")

            with mock.patch.object(evaluate_harbor_fit, "load_bucket_review_rules", return_value=fake_rules):
                with self.assertRaisesRegex(ValueError, "review request failed"):
                    evaluate_harbor_fit.evaluate_skill_bundle(
                        tmpdir,
                        bucket_slug="data-quality",
                        review_client=failing_review_client,
                    )

    def test_evaluate_skill_bundle_uses_truncated_bundle_when_first_file_exceeds_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "SKILL.md"), "w", encoding="utf-8") as stream:
                stream.write("x" * 200)

            fake_rules = make_fake_bucket_rules(max_markdown_files=2, max_total_characters=10)

            captured: dict[str, str] = {}

            def review_client(*, model, system_prompt, user_prompt):
                captured["user_prompt"] = user_prompt
                return {
                    "selected": True,
                    "decision": "keep",
                    "summary": "ok",
                    "matched_keep_rules": [
                        "bucket_fit",
                        "concrete_artifacts",
                        "self_contained_context",
                        "reproducible_environment",
                        "verifier_ready",
                    ],
                    "matched_drop_rules": [],
                    "confidence": "high",
                }

            with mock.patch.object(evaluate_harbor_fit, "load_bucket_review_rules", return_value=fake_rules):
                result = evaluate_harbor_fit.evaluate_skill_bundle(
                    tmpdir,
                    bucket_slug="data-quality",
                    review_client=review_client,
                )

        self.assertTrue(result["selected"])
        self.assertIn("# FILE: SKILL.md", captured["user_prompt"])

    def test_evaluate_skill_bundle_forces_drop_when_required_keep_rule_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "SKILL.md"), "w", encoding="utf-8") as stream:
                stream.write("skill content")

            def fake_review_client(*, model, system_prompt, user_prompt):
                return {
                    "selected": True,
                    "decision": "keep",
                    "summary": "model was optimistic",
                    "matched_keep_rules": ["bucket_fit", "concrete_artifacts"],
                    "matched_drop_rules": [],
                    "confidence": "medium",
                }

            with mock.patch.object(
                evaluate_harbor_fit,
                "load_bucket_review_rules",
                return_value=make_fake_bucket_rules(max_markdown_files=1, max_total_characters=500),
            ):
                result = evaluate_harbor_fit.evaluate_skill_bundle(
                    tmpdir,
                    bucket_slug="data-quality",
                    review_client=fake_review_client,
                )

        self.assertFalse(result["selected"])
        self.assertEqual(result["decision"], "drop")
        self.assertTrue(result["model_selected"])
        self.assertIn("self_contained_context", result["missing_required_keep_rules"])


class OpenAIReviewClientTests(unittest.TestCase):
    def test_resolve_openai_api_key_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_auth_path = os.path.join(tmpdir, "missing-auth.json")
            with mock.patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(openai_review_client.OpenAIReviewError):
                    openai_review_client.resolve_openai_api_key(auth_path=missing_auth_path)

    def test_resolve_openai_api_key_reads_codex_auth_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_path = os.path.join(tmpdir, "auth.json")
            with open(auth_path, "w", encoding="utf-8") as stream:
                json.dump({"OPENAI_API_KEY": "auth-key"}, stream)

            with mock.patch.dict(os.environ, {}, clear=True):
                api_key = openai_review_client.resolve_openai_api_key(auth_path=auth_path)

        self.assertEqual(api_key, "auth-key")

    def test_resolve_openai_base_url_prefers_env_var(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.toml")
            with open(config_path, "w", encoding="utf-8") as stream:
                stream.write(
                    """
model_provider = "sub2api"

[model_providers.sub2api]
base_url = "https://config.example.com"
"""
                )

            with mock.patch.dict(os.environ, {"OPENAI_BASE_URL": "https://env.example.com"}, clear=True):
                base_url = openai_review_client.resolve_openai_base_url(config_path=config_path)

        self.assertEqual(base_url, "https://env.example.com")

    def test_resolve_openai_base_url_reads_active_provider_from_codex_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.toml")
            with open(config_path, "w", encoding="utf-8") as stream:
                stream.write(
                    """
model_provider = "sub2api"

[model_providers.sub2api]
base_url = "https://fast.example.com"
"""
                )

            with mock.patch.dict(os.environ, {}, clear=True):
                base_url = openai_review_client.resolve_openai_base_url(config_path=config_path)

        self.assertEqual(base_url, "https://fast.example.com")

    def test_request_structured_review_parses_response_json(self):
        fake_result = {
            "selected": True,
            "decision": "keep",
            "summary": "ok",
            "matched_keep_rules": ["r1"],
            "matched_drop_rules": [],
            "confidence": "high",
        }
        fake_response = {
            "id": "resp_123",
            "output": [{"content": [{"text": json.dumps(fake_result)}]}],
        }

        mock_http_response = mock.Mock()
        mock_http_response.raise_for_status.return_value = None
        mock_http_response.json.return_value = fake_response

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with mock.patch("top20_search.src.openai_review_client.requests.post", return_value=mock_http_response):
                parsed = openai_review_client.request_structured_review(
                    model="gpt-5.4-mini",
                    system_prompt="sys",
                    user_prompt="usr",
                )

        self.assertEqual(parsed["selected"], True)
        self.assertEqual(parsed["decision"], "keep")
        self.assertEqual(parsed["raw_response_id"], "resp_123")

    def test_request_structured_review_parses_message_after_reasoning_item(self):
        fake_result = {
            "selected": True,
            "decision": "keep",
            "summary": "ok",
            "matched_keep_rules": ["r1"],
            "matched_drop_rules": [],
            "confidence": "high",
        }
        fake_response = {
            "id": "resp_123",
            "output": [
                {"id": "rs_1", "type": "reasoning", "summary": []},
                {
                    "id": "msg_1",
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(fake_result)}],
                },
            ],
        }

        mock_http_response = mock.Mock()
        mock_http_response.raise_for_status.return_value = None
        mock_http_response.json.return_value = fake_response

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with mock.patch("top20_search.src.openai_review_client.requests.post", return_value=mock_http_response):
                parsed = openai_review_client.request_structured_review(
                    model="gpt-5.4-mini",
                    system_prompt="sys",
                    user_prompt="usr",
                )

        self.assertEqual(parsed["decision"], "keep")

    def test_request_structured_review_uses_resolved_base_url(self):
        fake_result = {
            "selected": True,
            "decision": "keep",
            "summary": "ok",
            "matched_keep_rules": ["r1"],
            "matched_drop_rules": [],
            "confidence": "high",
        }
        fake_response = {
            "id": "resp_123",
            "output": [{"content": [{"text": json.dumps(fake_result)}]}],
        }

        mock_http_response = mock.Mock()
        mock_http_response.raise_for_status.return_value = None
        mock_http_response.json.return_value = fake_response

        captured_request = {}

        def fake_post(url, json, headers, timeout):
            captured_request["url"] = url
            captured_request["payload"] = json
            captured_request["headers"] = headers
            captured_request["timeout"] = timeout
            return mock_http_response

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with mock.patch(
                "top20_search.src.openai_review_client.resolve_openai_base_url",
                return_value="https://fast.example.com",
            ):
                with mock.patch("top20_search.src.openai_review_client.requests.post", side_effect=fake_post):
                    openai_review_client.request_structured_review(
                        model="gpt-5.4-mini",
                        system_prompt="sys",
                        user_prompt="usr",
                    )

        self.assertEqual(captured_request["url"], "https://fast.example.com/v1/responses")
        self.assertEqual(captured_request["timeout"], 60)
        self.assertEqual(captured_request["headers"]["Accept"], "application/json")
        self.assertEqual(captured_request["headers"]["User-Agent"], "Harbor-top20-search/1.0")

    def test_request_structured_review_rejects_invalid_response_payload(self):
        fake_response = {"id": "resp_123", "output": []}
        mock_http_response = mock.Mock()
        mock_http_response.raise_for_status.return_value = None
        mock_http_response.json.return_value = fake_response

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with mock.patch("top20_search.src.openai_review_client.requests.post", return_value=mock_http_response):
                with self.assertRaises(openai_review_client.OpenAIReviewError):
                    openai_review_client.request_structured_review(
                        model="gpt-5.4-mini",
                        system_prompt="sys",
                        user_prompt="usr",
                    )

    def test_request_structured_review_retries_transient_http_error(self):
        fake_result = {
            "selected": True,
            "decision": "keep",
            "summary": "ok",
            "matched_keep_rules": ["r1"],
            "matched_drop_rules": [],
            "confidence": "high",
        }
        fake_response = {
            "id": "resp_123",
            "output": [{"content": [{"text": json.dumps(fake_result)}]}],
        }

        transient_response = mock.Mock()
        transient_response.status_code = 503
        transient_response.text = '{"error":{"message":"Service temporarily unavailable"}}'
        transient_error = requests.HTTPError("503 Server Error", response=transient_response)
        transient_response.raise_for_status.side_effect = transient_error

        ok_response = mock.Mock()
        ok_response.raise_for_status.return_value = None
        ok_response.json.return_value = fake_response

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with mock.patch(
                "top20_search.src.openai_review_client.requests.post",
                side_effect=[transient_response, ok_response],
            ) as post_mock, mock.patch(
                "top20_search.src.openai_review_client.time.sleep"
            ) as sleep_mock:
                parsed = openai_review_client.request_structured_review(
                    model="gpt-5.4-mini",
                    system_prompt="sys",
                    user_prompt="usr",
                )

        self.assertTrue(parsed["selected"])
        self.assertEqual(post_mock.call_count, 2)
        sleep_mock.assert_called_once()
