#!/usr/bin/env python3
"""Refresh the complete subscription table in README.md."""

from __future__ import annotations

import json
import argparse
from pathlib import Path


START = "<!-- BEGIN GENERATED CATALOG -->"
END = "<!-- END GENERATED CATALOG -->"
RAW_ROOT = "https://raw.githubusercontent.com/marcomc/glinet-vpn-subscription-lists/main"
VARIANT_SUFFIXES = (
    "-all-v4", "-all-v6", "-ips-v4", "-ips-v6", "-domains", "-ips", "-all"
)


def render(root: Path) -> str:
    report = json.loads((root / "reports/coverage.json").read_text(encoding="utf-8"))
    lists = report["lists"]
    artifacts = report["artifacts"]
    legacy = {f"output/{details['provider']}/{name}.txt": name
              for name, details in lists.items()}
    expected = set(legacy) | set(artifacts)
    actual = {str(path.relative_to(root)) for path in (root / "output").rglob("*.txt")}
    if actual != expected:
        raise ValueError(f"catalog does not match output files: {sorted(actual ^ expected)}")

    rows = []
    for relative in sorted(expected):
        if relative in legacy:
            base = legacy[relative]
            counts = (lists[base]["domains"], 0, 0)
        else:
            stem = Path(relative).stem
            base = next((stem[:-len(suffix)] for suffix in VARIANT_SUFFIXES
                         if stem.endswith(suffix)), None)
            if base not in lists:
                raise ValueError(f"unknown service for {relative}")
            details = artifacts[relative]
            counts = tuple(details[key] for key in
                           ("domains", "ipv4_cidrs", "ipv6_cidrs"))
        if len((root / relative).read_text(encoding="utf-8").splitlines()) != sum(counts):
            raise ValueError(f"count mismatch for {relative}")
        service = lists[base]
        link = f"[{Path(relative).name}]({RAW_ROOT}/{relative})"
        rows.append(f"| {service['provider']} / {service['service']} | {link} | "
                    f"{counts[0]} | {counts[1]} | {counts[2]} |")

    return "\n".join((
        f"Last successful update: `{report['last_successful_update']}`. "
        f"The table contains all {len(rows)} published files.",
        "",
        "| Provider / service | Subscription URL | Domains | IPv4 CIDRs | IPv6 CIDRs |",
        "| --- | --- | ---: | ---: | ---: |",
        *rows,
    ))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True,
                        help="lists repository root containing README.md and output/")
    args = parser.parse_args()
    root = args.root.resolve()
    readme = root / "README.md"
    original = readme.read_text(encoding="utf-8")
    if original.count(START) != 1 or original.count(END) != 1:
        raise ValueError("README.md must contain one catalog marker pair")
    before, remainder = original.split(START, 1)
    _, after = remainder.split(END, 1)
    updated = f"{before}{START}\n\n{render(root)}\n\n{END}{after}"
    if updated != original:
        readme.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
