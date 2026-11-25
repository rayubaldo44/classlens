import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from scripts.audit_python_lock import main


HASH = "a" * 64
CPU_WHEEL = (
    "https://download-r2.pytorch.org/whl/cpu/"
    "torch-2.13.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl"
)
LOCK = f"""# Linux/WSL x86-64
--index-url https://pypi.org/simple
--only-binary :all:
--require-hashes
certifi==2026.10.18 --hash=sha256:{HASH}
torch @ {CPU_WHEEL} --hash=sha256:{HASH}
"""


class AuditPythonLockTests(unittest.TestCase):
    def run_audit(self, lock=LOCK, response=None, error=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "requirements.lock"
            path.write_text(lock, encoding="utf-8")
            stdout, stderr = io.StringIO(), io.StringIO()
            with (
                patch("scripts.audit_python_lock.urlopen") as post,
                patch("sys.stdout", stdout),
                patch("sys.stderr", stderr),
            ):
                post.return_value = io.BytesIO(json.dumps(response).encode("utf-8"))
                post.side_effect = error
                status = main([str(path)])
            request = post.call_args.args[0] if post.called else None
            return status, stdout.getvalue(), stderr.getvalue(), request

    def test_queries_every_locked_distribution_and_normalizes_cpu_torch(self):
        status, stdout, stderr, request = self.run_audit(response={"results": [{}, {}]})
        self.assertEqual(status, 0, stderr)
        self.assertIn("2 locked distributions", stdout)
        self.assertEqual(request.full_url, "https://api.osv.dev/v1/querybatch")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(
            json.loads(request.data),
            {
                "queries": [
                    {"package": {"ecosystem": "PyPI", "name": "certifi"}, "version": "2026.10.18"},
                    {"package": {"ecosystem": "PyPI", "name": "torch"}, "version": "2.13.0"},
                ]
            },
        )

    def test_reports_matching_package_and_fails(self):
        status, _, stderr, _ = self.run_audit(
            response={"results": [{}, {"vulns": [{"id": "GHSA-example"}]}]}
        )
        self.assertEqual(status, 1)
        self.assertIn("torch==2.13.0", stderr)
        self.assertIn("GHSA-example", stderr)

    def test_rejects_missing_or_malformed_osv_results(self):
        for response in (
            {},
            {"results": [{}]},
            {"results": [{}, {}, {}]},
            {"results": [{}, {"error": "failed"}]},
            {"results": [{}, {"vulns": None}]},
            {"results": [{}, {"vulns": [{}]}]},
        ):
            with self.subTest(response=response):
                status, _, stderr, _ = self.run_audit(response=response)
                self.assertEqual(status, 2)
                self.assertIn("OSV", stderr)

    def test_rejects_unavailable_osv(self):
        status, _, stderr, _ = self.run_audit(error=URLError("unavailable"))
        self.assertEqual(status, 2)
        self.assertIn("unavailable", stderr)

    def test_rejects_unparsed_or_duplicate_requirements_before_contacting_osv(self):
        for lock in (
            "",
            LOCK.replace("certifi==2026.10.18", "certifi>=2026.10.18"),
            LOCK.replace("download-r2.pytorch.org", "example.org"),
            LOCK.replace(f"--hash=sha256:{HASH}", ""),
            LOCK + f"Certifi==2026.10.18 --hash=sha256:{HASH}\n",
            LOCK + "--extra-index-url https://example.org/simple\n",
        ):
            with self.subTest(lock=lock):
                status, _, stderr, request = self.run_audit(lock=lock)
                self.assertEqual(status, 2)
                self.assertIn("requirements.lock", stderr)
                self.assertIsNone(request)
