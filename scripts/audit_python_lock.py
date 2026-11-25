"""Audit every version in the ClassLens hash-checked Python lock with OSV."""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen


OSV_QUERY_BATCH = "https://api.osv.dev/v1/querybatch"
LOCK_OPTIONS = {
    "--index-url https://pypi.org/simple",
    "--only-binary :all:",
    "--require-hashes",
}
HASH = r" --hash=sha256:[0-9a-f]{64}"
PIN = re.compile(r"([A-Za-z0-9][A-Za-z0-9_.-]*)==([0-9][A-Za-z0-9.!+_-]*)" + HASH)
TORCH_CPU_WHEEL = re.compile(
    r"torch @ https://download-r2\.pytorch\.org/whl/cpu/"
    r"torch-([0-9]+\.[0-9]+\.[0-9]+)%2Bcpu-cp311-cp311-manylinux_2_28_x86_64\.whl"
    + HASH
)


def read_lock(path: Path) -> dict[str, str]:
    packages = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#") or line in LOCK_OPTIONS:
            continue

        wheel = TORCH_CPU_WHEEL.fullmatch(line)
        pin = PIN.fullmatch(line)
        if wheel:
            # OSV identifies CPU builds by the upstream public release version.
            name, version = "torch", wheel.group(1)
        elif pin:
            name = re.sub(r"[-_.]+", "-", pin.group(1)).lower()
            version = pin.group(2)
            if name == "torch":
                raise ValueError(f"{path}:{number} must pin Torch to its official CPU wheel")
        else:
            raise ValueError(f"{path}:{number} is not a supported hash-checked lock entry")

        if name in packages:
            raise ValueError(f"{path}:{number} duplicates {name}")
        packages[name] = version

    if "torch" not in packages:
        raise ValueError(f"{path} is missing its pinned Torch CPU wheel")
    return packages


def audit(packages: dict[str, str]) -> list[tuple[str, str]]:
    queries = [
        {"package": {"ecosystem": "PyPI", "name": name}, "version": version}
        for name, version in packages.items()
    ]
    request = Request(
        OSV_QUERY_BATCH,
        data=json.dumps({"queries": queries}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        document = json.load(response)
    results = document.get("results") if isinstance(document, dict) else None
    if not isinstance(results, list) or len(results) != len(queries):
        raise ValueError("OSV did not return one result per locked distribution")

    findings = []
    for package, result in zip(packages.items(), results, strict=True):
        if not isinstance(result, dict) or result.keys() - {"vulns"}:
            raise ValueError("OSV returned an invalid result")
        vulnerabilities = result.get("vulns", [])
        if not isinstance(vulnerabilities, list):
            raise ValueError("OSV returned an invalid vulnerability list")
        name, version = package
        for vulnerability in vulnerabilities:
            advisory = vulnerability.get("id") if isinstance(vulnerability, dict) else None
            if not isinstance(advisory, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", advisory):
                raise ValueError("OSV returned a missing or invalid advisory ID")
            findings.append((f"{name}=={version}", advisory))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lock", type=Path)
    args = parser.parse_args(argv)

    try:
        packages = read_lock(args.lock)
        findings = audit(packages)
    except (OSError, ValueError) as error:
        print(f"Python dependency audit failed: {error}", file=sys.stderr)
        return 2

    if findings:
        for package, advisory in findings:
            print(f"{package}: {advisory}", file=sys.stderr)
        return 1

    print(f"OSV reported no matches for {len(packages)} locked distributions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
