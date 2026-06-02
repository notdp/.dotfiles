import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FETCH_SCRIPT = REPO_ROOT / "coding-skills" / "web-read" / "scripts" / "fetch.sh"


class WebReadFetchTests(unittest.TestCase):
    def test_fetch_script_routes_github_urls_through_reader_proxy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            fakebin = tmpdir / "fakebin"
            fakebin.mkdir()
            requested_url = tmpdir / "requested-url.txt"
            output_file = tmpdir / "result.md"
            curl_script = fakebin / "curl"
            curl_script.write_text(
                f"""#!/bin/sh
set -eu
outfile=""
url=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    -o)
      outfile="$2"
      shift 2
      ;;
    -*)
      shift
      ;;
    *)
      url="$1"
      shift
      ;;
  esac
done
printf '%s' "$url" > "{requested_url}"
printf '%s\\n' '# fetched markdown' > "$outfile"
"""
            )
            os.chmod(curl_script, 0o755)

            result = subprocess.run(
                ["bash", str(FETCH_SCRIPT), "https://github.com/tw93/Waza/blob/main/README.md", str(output_file)],
                text=True,
                capture_output=True,
                env={**os.environ, "PATH": f"{fakebin}:{os.environ['PATH']}"},
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertEqual(output_file.read_text(), "# fetched markdown\n")
            self.assertEqual(
                requested_url.read_text(),
                "https://r.jina.ai/http://github.com/tw93/Waza/blob/main/README.md",
            )


if __name__ == "__main__":
    unittest.main()
