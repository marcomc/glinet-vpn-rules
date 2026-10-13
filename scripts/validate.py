#!/usr/bin/env python3
"""Validate every published subscription against the router-safe format."""
from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path

if __package__:
    from .generate import ROOT, normalize
    from .ip_rules import normalized_network, sorted_networks
else:
    from generate import ROOT, normalize
    from ip_rules import normalized_network, sorted_networks


def validate(root: Path = ROOT) -> None:
    report = json.loads((root / "reports/coverage.json").read_text())
    artifacts = report["artifacts"]
    paths = sorted((root / "output").rglob("*.txt"))
    expected = set(artifacts)
    actual = {str(path.relative_to(root)) for path in paths}
    if actual != expected:
        raise ValueError(f"unexpected or missing subscriptions: {sorted(actual ^ expected)}")
    for path in paths:
        relative = str(path.relative_to(root))
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines or len(lines) != len(set(lines)):
            raise ValueError(f"empty or duplicate lines: {relative}")
        domains, networks = [], []
        for number, line in enumerate(lines, 1):
            if "/" in line:
                try:
                    network = normalized_network(line)
                except ValueError as exc:
                    raise ValueError(f"invalid CIDR at {relative}:{number}: {line}") from exc
                if str(network) != line:
                    raise ValueError(f"noncanonical CIDR at {relative}:{number}: {line}")
                networks.append(network)
            elif normalize(line) == line:
                domains.append(line)
            else:
                raise ValueError(f"router-incompatible domain at {relative}:{number}: {line}")
        if lines != sorted(domains) + [str(network) for network in sorted_networks(networks)]:
            raise ValueError(f"nondeterministic or overlapping entries: {relative}")
        if relative in artifacts:
            expected_counts = artifacts[relative]
            counts = (len(domains), sum(isinstance(network, ipaddress.IPv4Network) for network in networks),
                      sum(isinstance(network, ipaddress.IPv6Network) for network in networks))
            if counts != tuple(expected_counts[key] for key in ("domains", "ipv4_cidrs", "ipv6_cidrs")):
                raise ValueError(f"report count mismatch: {relative}")
        if path.name.endswith("-ips.txt"):
            base = path.name[:-8]
            provenance = report["ip_ranges"].get(base)
            if provenance is None or set(provenance) != {str(network) for network in networks}:
                raise ValueError(f"IP provenance mismatch: {relative}")
            for cidr, item in provenance.items():
                if not item.get("source_urls") or not item.get("source_updated_at") or not item.get("retrieved_at"):
                    raise ValueError(f"incomplete IP provenance: {cidr}")
    google = set((root / "output/google/google-all-domains.txt").read_text().splitlines())
    services = set().union(*(set(path.read_text().splitlines()) for path in
                             (root / "output/google").glob("google-*.txt")
                             if path.name in {f"{name}-domains.txt" for name in report["lists"] if name.startswith("google-") and name != "google-all"}))
    if google != services:
        raise ValueError("google-all is not the union of Google service domains")
    for base, provenance in report["ip_ranges"].items():
        provider = base.split("-", 1)[0]
        directory = root / "output" / provider
        source_ranges = {str(normalized_network(cidr)) for cidr in provenance}
        ipv4 = {cidr for cidr in source_ranges if "." in cidr}
        ipv6 = source_ranges - ipv4
        domain_path = directory / f"{base}-domains.txt"
        domains = set(domain_path.read_text().splitlines())
        expected_lists = {
            f"{base}-ips-v4.txt": ipv4,
            f"{base}-ips-v6.txt": ipv6,
            f"{base}-ips.txt": source_ranges,
            f"{base}-combined-v4.txt": domains | ipv4,
            f"{base}-combined-v6.txt": domains | ipv6,
            f"{base}-combined.txt": domains | source_ranges,
        }
        for filename, expected_lines in expected_lists.items():
            artifact = directory / filename
            # The generator omits an address-family variant when its source
            # publishes no ranges for that family.
            if filename.endswith(('-ips-v4.txt', '-ips-v6.txt', '-combined-v4.txt', '-combined-v6.txt')) and not (
                ipv4 if filename.endswith('-v4.txt') else ipv6
            ):
                if artifact.exists():
                    raise ValueError(f"unexpected empty address-family list: {artifact}")
                continue
            actual_lines = set(artifact.read_text().splitlines())
            if actual_lines != expected_lines:
                raise ValueError(f"combined-list mismatch: {artifact}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True,
                        help="repository root containing output/ and reports/coverage.json")
    args = parser.parse_args()
    validate(args.root.resolve())
    print("All published subscriptions and CIDR provenance validated")
