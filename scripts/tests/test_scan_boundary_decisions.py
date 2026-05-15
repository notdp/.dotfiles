import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_SCRIPT = REPO_ROOT / "scripts" / "scan_boundary_decisions.py"


class ScanBoundaryDecisionsTests(unittest.TestCase):
    def run_scan(self, diff: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCAN_SCRIPT), "--stdin"],
            input=diff,
            text=True,
            capture_output=True,
        )

    def run_hook_scan(self, diff: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCAN_SCRIPT), "--stdin", "--hook"],
            input=diff,
            text=True,
            capture_output=True,
        )

    def test_reports_high_signal_boundary_changes(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/service.py b/src/service.py
            --- a/src/service.py
            +++ b/src/service.py
            @@ -10,2 +10,13 @@ def handler(posts):
             keep()
            +if len(posts) > 4:
            +    raise HTTPException(status_code=422, detail="too many")
            +if not user:
            +    return JSONResponse({"error": "missing"}, status_code=400)
            +assert len(posts) <= 4
            +try:
            +    risky()
            +except Exception:
            +    pass
            +items = payload.get("items") or []
            +time.sleep(1)
            +return result
            diff --git a/src/metrics.py b/src/metrics.py
            --- a/src/metrics.py
            +++ b/src/metrics.py
            @@ -1,1 +1,3 @@
             keep()
            +StatsStore.counter("creator.incremental.path", labels={"mode": "incremental"}).emit(1)
            +metrics.gauge("country.service.latency", latency_ms, label="wrapper")
            diff --git a/src/api.ts b/src/api.ts
            --- a/src/api.ts
            +++ b/src/api.ts
            @@ -1,1 +1,4 @@
             keep()
            +export interface CreatorResponse {
            +  success: boolean
            +  data: Creator
            +}
            """
        )

        result = self.run_scan(diff)

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("| rejection | src/service.py | 12 |", result.stdout)
        self.assertIn("| implicit-branch | src/service.py | 11 |", result.stdout)
        self.assertIn("| assert-guard | src/service.py | 15 |", result.stdout)
        self.assertIn("| silent-catch | src/service.py | 18 |", result.stdout)
        self.assertIn("| default-value | src/service.py | 20 |", result.stdout)
        self.assertIn("| retry-backoff | src/service.py | 21 |", result.stdout)
        self.assertIn("| observability-routing | src/metrics.py | 2 |", result.stdout)
        self.assertIn("| schema-contract | src/api.ts | 2 |", result.stdout)

    def test_ignores_context_removed_docs_tests_and_scanner_source(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/docs/spec.md b/docs/spec.md
            --- a/docs/spec.md
            +++ b/docs/spec.md
            @@ -1,1 +1,2 @@
             keep()
            +raise HTTPException(status_code=422)
            diff --git a/docs/boundary-guide.html b/docs/boundary-guide.html
            --- a/docs/boundary-guide.html
            +++ b/docs/boundary-guide.html
            @@ -1,1 +1,2 @@
             keep()
            +<li>retry backoff schema response_model metric</li>
            diff --git a/scripts/tests/fixture.py b/scripts/tests/fixture.py
            --- a/scripts/tests/fixture.py
            +++ b/scripts/tests/fixture.py
            @@ -1,1 +1,2 @@
             keep()
            +assert len(posts) <= 4
            diff --git a/scripts/scan_boundary_decisions.py b/scripts/scan_boundary_decisions.py
            --- a/scripts/scan_boundary_decisions.py
            +++ b/scripts/scan_boundary_decisions.py
            @@ -1,1 +1,2 @@
             keep()
            +time.sleep(1)
            diff --git a/scripts/hook_boundary_gate.py b/scripts/hook_boundary_gate.py
            --- a/scripts/hook_boundary_gate.py
            +++ b/scripts/hook_boundary_gate.py
            @@ -1,1 +1,4 @@
             keep()
            +except json.JSONDecodeError:
            +    return {}
            +r"schema|response_model|metric"
            diff --git a/src/app.py b/src/app.py
            --- a/src/app.py
            +++ b/src/app.py
            @@ -10,3 +10,3 @@ def handler():
             raise HTTPException(status_code=422)
            -return JSONResponse({"error": "old"}, status_code=400)
            +return ok()
            """
        )

        result = self.run_scan(diff)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("命中 0 条", result.stdout)

    def test_hook_mode_uses_fixed_additional_context_prefix(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/api.py b/src/api.py
            --- a/src/api.py
            +++ b/src/api.py
            @@ -1,1 +1,2 @@
             keep()
            +@router.get("/creator", response_model=CreatorEnvelope)
            """
        )

        result = self.run_hook_scan(diff)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(context.startswith("Boundary decision scan found"))

    def test_scans_untracked_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            src = repo / "src"
            src.mkdir()
            (src / "service.py").write_text(
                "from fastapi import HTTPException\nraise HTTPException(status_code=422)\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", str(SCAN_SCRIPT)],
                cwd=repo,
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("| rejection | src/service.py | 2 |", result.stdout)


if __name__ == "__main__":
    unittest.main()
