import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "hooks" / "redact.py"


def load_redact_module():
    spec = importlib.util.spec_from_file_location("dotfiles_redact", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RedactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.redact = load_redact_module()

    def test_detects_required_secret_families(self) -> None:
        samples = {
            "aws": "aws_access_key_id=AKIAIOSFODNN7EXAMPLE",
            "github": "token=ghp_abcdefghijklmnopqrstuvwxyz1234567890AB",
            "jwt": "jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
            "pem": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----",
            "connection": "postgres://user:secretpass@localhost:5432/app",
            "assigned_entropy": "api_key=abcdefghijklmnopqrstuvwxyz1234567890ABCD",
            "natural_language": "the production secret is correct horse battery staple",
        }
        for family, text in samples.items():
            with self.subTest(family=family):
                findings = self.redact.find_secret_findings(text)
                self.assertTrue(findings, family)
                with self.assertRaises(self.redact.SecretFoundError):
                    self.redact.assert_no_secrets(text, source=family)

    def test_precision_allows_legitimate_hashes_and_candidate_filenames(self) -> None:
        allowed = [
            "commit 2f1c3d4e5f678901234567890abcdef123456789",
            "md5 checksum d41d8cd98f00b204e9800998ecf8427e",
            "sha256 checksum e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "raw memory candidate sha256-e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.json",
            "proxy placeholder http://username:password@proxy.example.com:8080",
            "proxy placeholder socks5://user:pass@proxy.example.com:1080",
        ]
        for text in allowed:
            with self.subTest(text=text):
                self.assertEqual(self.redact.find_secret_findings(text), [])
                self.redact.assert_no_secrets(text, source="precision")

    def test_redact_masks_secrets_and_urls_for_context_state(self) -> None:
        text = "token=ghp_abcdefghijklmnopqrstuvwxyz1234567890AB at https://secret.example.com/path"
        redacted = self.redact.redact(text)
        self.assertIn("[REDACTED_SECRET]", redacted)
        self.assertIn("[REDACTED_URL]", redacted)
        self.assertNotIn("ghp_", redacted)
        self.assertNotIn("secret.example.com", redacted)

    def test_scan_repo_reports_root_secret_and_excludes_runtime_private_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret = "token=ghp_abcdefghijklmnopqrstuvwxyz1234567890AB\n"
            (root / "leak.txt").write_text(secret, encoding="utf-8")
            for relative in [
                "memory/.staging/raw_memories/leak.json",
                "memory/.local/leak.txt",
                ".long-loop/leak.txt",
                ".agent-state/leak.txt",
            ]:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(secret, encoding="utf-8")

            findings, skipped = self.redact.scan_repo(root)

        self.assertEqual(skipped, [])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0][0].name, "leak.txt")

    def test_scan_repo_logs_undecodable_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bad.txt").write_bytes(b"\xff\xfe\x00")

            result = subprocess.run(
                ["python3", str(MODULE_PATH), "scan-repo", str(root)],
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("secret scan skipped 1 undecodable/unreadable file(s)", result.stderr)
        self.assertIn("secret scan passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
