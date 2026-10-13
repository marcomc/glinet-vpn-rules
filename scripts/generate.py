#!/usr/bin/env python3
"""Generate conservative GL.iNet plain-text domain subscriptions."""
from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import re
import tempfile
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

import yaml

if __package__:
    from .ip_rules import normalized_network, resolve_ip_source
else:
    from ip_rules import normalized_network, resolve_ip_source

ROOT = Path(__file__).resolve().parents[1]
HOST = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.I)
USER_AGENT = "glinet-vpn-subscription-generator/1.0.0 (public GitHub Actions generator)"


def normalize(value: str) -> str | None:
    value = value.strip().rstrip(".").lower()
    if not value or "/" in value or ":" in value or "*" in value:
        return None
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    if not HOST.fullmatch(value) or "." not in value:
        return None
    # GL.iNet's Subscription URL parser rejects digit-leading hostnames even
    # though DNS permits them (observed for the first seven google-all entries).
    if any(label[0].isdigit() for label in value.split(".")):
        return None
    return value


def invalid_domain_reason(value: str) -> str:
    candidate = value.removeprefix("full:").removeprefix("+.").strip().rstrip(".").lower()
    if candidate and any(label[0].isdigit() for label in candidate.split(".") if label):
        return "digit-leading domain label rejected by GL.iNet subscription parser"
    return "invalid or unsupported domain"


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=35) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        return response.read(4_000_001).decode("utf-8-sig")


def parse_v2fly(text: str) -> tuple[set[str], list[dict], list[str]]:
    domains, unsupported, includes = set(), [], []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        item = line.split()[0]
        if item.startswith("include:"):
            includes.append(item[8:])
            continue
        if item.startswith("full:"):
            item = item[5:]
        elif item.startswith(("regexp:", "keyword:")):
            unsupported.append({"line": number, "rule": line, "reason": "regex or keyword"})
            continue
        domain = normalize(item)
        if domain:
            domains.add(domain)
        else:
            unsupported.append({"line": number, "rule": line, "reason": invalid_domain_reason(item)})
    return domains, unsupported, includes


def parse_meta(text: str) -> tuple[set[str], list[dict]]:
    document = yaml.safe_load(text)
    if not isinstance(document, dict) or not isinstance(document.get("payload"), list):
        raise ValueError("invalid MetaCubeX payload")
    domains, unsupported = set(), []
    for number, item in enumerate(document["payload"], 1):
        if not isinstance(item, str):
            unsupported.append({"line": number, "rule": repr(item), "reason": "non-string payload"})
            continue
        domain = normalize(item.removeprefix("+."))
        if domain:
            domains.add(domain)
        else:
            unsupported.append({"line": number, "rule": item, "reason": invalid_domain_reason(item)})
    return domains, unsupported


def parse_clash(text: str) -> tuple[set[str], list[dict]]:
    domains, unsupported = set(), []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) >= 2 and parts[0] in {"DOMAIN", "DOMAIN-SUFFIX"}:
            domain = normalize(parts[1])
            if domain:
                domains.add(domain)
                continue
            unsupported.append({"line": number, "rule": line, "reason": invalid_domain_reason(parts[1])})
            continue
        unsupported.append({"line": number, "rule": line, "reason": "unsupported Clash rule"})
    return domains, unsupported


class Resolver:
    def __init__(self, sources: dict):
        self.sources = sources
        self.cache: dict[str, set[str]] = {}
        self.unsupported: dict[str, list[dict]] = defaultdict(list)
        self.urls: dict[str, str] = {}

    def resolve(self, key: str, stack: tuple[str, ...] = ()) -> set[str]:
        if key in stack:
            raise ValueError("circular source include: " + " -> ".join((*stack, key)))
        if key in self.cache:
            return self.cache[key]
        if key not in self.sources:
            raise ValueError(f"unknown source: {key}")
        spec = self.sources[key]
        result: set[str] = set()
        if "url" in spec:
            url = spec["url"]
            self.urls[key] = url
            content = fetch(url)
            if spec["format"] == "v2fly":
                parsed, missing, includes = parse_v2fly(content)
                self.unsupported[key].extend(missing)
                result.update(parsed)
                for child in includes:
                    child_key = f"v2fly:{child}"
                    if child_key not in self.sources:
                        self.sources[child_key] = {"url": f"https://raw.githubusercontent.com/v2fly/domain-list-community/master/data/{child}", "format": "v2fly"}
                    result.update(self.resolve(child_key, (*stack, key)))
            elif spec["format"] == "meta":
                parsed, missing = parse_meta(content)
                self.unsupported[key].extend(missing)
                result.update(parsed)
            elif spec["format"] == "clash":
                parsed, missing = parse_clash(content)
                self.unsupported[key].extend(missing)
                result.update(parsed)
            else:
                raise ValueError(f"unsupported source format: {spec['format']}")
        for item in spec.get("domains", []):
            domain = normalize(item)
            if not domain:
                raise ValueError(f"invalid configured domain: {key}: {item}")
            result.add(domain)
        for child in spec.get("include", []):
            result.update(self.resolve(child, (*stack, key)))
        self.cache[key] = result
        return result


def generate(config: dict, resolver: Resolver) -> tuple[dict[str, set[str]], dict]:
    outputs: dict[str, set[str]] = {}
    details = {}
    for provider, services in config["providers"].items():
        for service, spec in services.items():
            name = f"{provider}-{service}"
            if service == "all" and provider == "google":
                continue
            domains = set()
            for source in sorted(spec.get("sources", []), key=lambda key: resolver.sources[key].get("priority", 100)):
                domains.update(resolver.resolve(source))
            for other in spec.get("include", []):
                key = f"{provider}-{other}"
                if key not in outputs:
                    raise ValueError(f"service include must precede {name}: {key}")
                domains.update(outputs[key])
            for excluded in spec.get("exclude", []):
                domain = normalize(excluded)
                if not domain:
                    raise ValueError(f"invalid exclusion: {excluded}")
                domains.discard(domain)
            if spec.get("remaining"):
                for previous, values in outputs.items():
                    if previous.startswith(provider + "-"):
                        domains.difference_update(values)
            if not domains:
                raise ValueError(f"empty output: {name}")
            outputs[name] = domains
            details[name] = spec
    google = set().union(*(values for name, values in outputs.items() if name.startswith("google-")))
    outputs["google-all"] = google
    details["google-all"] = config["providers"]["google"]["all"]
    for provider, services in config["providers"].items():
        for service, spec in services.items():
            name = f"{provider}-{service}"
            expected = f"output/{provider}/{name}-domains.txt"
            if spec["output"] != expected or name not in outputs:
                raise ValueError(f"invalid output mapping: {name}")
    return outputs, details


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config/services.yml")
    parser.add_argument("--output-root", type=Path, required=True,
                        help="repository root where output/ and reports/ are written")
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    config = yaml.safe_load(args.config.read_text())
    resolver = Resolver(config["sources"].copy())
    outputs, details = generate(config, resolver)
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    report = {"last_successful_update": timestamp, "lists": {}, "artifacts": {}, "ip_ranges": {},
              "unsupported_rules": resolver.unsupported,
              "limitations": ["GL.iNet documents bare domains as suffix matches and full subdomains as exact matches; nested upstream suffix rules may under-match descendants.", "Domain routing depends on router-visible DNS; encrypted or external DNS may bypass it.", "Shared infrastructure can route unrelated services; no Google Cloud customer IP ranges are included."]}
    planned: dict[Path, str] = {}
    for name, domains in outputs.items():
        provider, service = name.split("-", 1)
        spec = details[name]
        source_keys = spec.get("sources", [])
        domain_lines = sorted(domains)
        for domain in domain_lines:
            if normalize(domain) != domain:
                raise ValueError(f"router-incompatible domain in {name}: {domain}")
        domain_content = "\n".join(domain_lines) + "\n"
        domains_path = output_root / spec["output"]
        planned[domains_path] = domain_content
        report["artifacts"][str(domains_path.relative_to(output_root))] = {"domains": len(domains), "ipv4_cidrs": 0, "ipv6_cidrs": 0}
        report["lists"][name] = {"provider": provider, "service": service, "domains": len(domains),
                                  "sources": source_keys, "last_successful_update": timestamp,
                                  "unsupported_rules": sum(len(resolver.unsupported.get(key, [])) for key in source_keys),
                                  "coverage_limitations": spec.get("limitations", [])}
    for name, source_key in config.get("ip_lists", {}).items():
        if name not in outputs:
            raise ValueError(f"unknown IP list target: {name}")
        if source_key not in config.get("ip_sources", {}):
            raise ValueError(f"unknown IP source: {source_key}")
        result = resolve_ip_source(config["ip_sources"][source_key], timestamp)
        provider = name.split("-", 1)[0]
        service_domain_lines = sorted(outputs[name])
        directory = output_root / "output" / provider
        ip_lines = [str(network) for network in result.networks]
        for line in ip_lines:
            if str(normalized_network(line)) != line:
                raise ValueError(f"invalid generated CIDR: {line}")
        ipv4_lines = [str(network) for network in result.networks if isinstance(network, ipaddress.IPv4Network)]
        ipv6_lines = [str(network) for network in result.networks if isinstance(network, ipaddress.IPv6Network)]
        variants = {
            f"{name}-ips-v4.txt": ([], ipv4_lines),
            f"{name}-ips-v6.txt": ([], ipv6_lines),
            f"{name}-ips.txt": ([], ip_lines),
            f"{name}-combined-v4.txt": (service_domain_lines, ipv4_lines),
            f"{name}-combined-v6.txt": (service_domain_lines, ipv6_lines),
            f"{name}-combined.txt": (service_domain_lines, ip_lines),
        }
        for filename, (variant_domains, variant_ips) in variants.items():
            if not variant_ips:
                continue
            destination = directory / filename
            planned[destination] = "\n".join(variant_domains + variant_ips) + "\n"
            report["artifacts"][str(destination.relative_to(output_root))] = {
                "domains": len(variant_domains),
                "ipv4_cidrs": sum("." in line for line in variant_ips),
                "ipv6_cidrs": sum(":" in line for line in variant_ips),
                "source": source_key, "source_urls": result.sources,
                "source_updated_at": result.source_updated_at, "retrieved_at": result.retrieved_at,
            }
        report["ip_ranges"][name] = {
            line: {"source": source_key, "source_urls": result.sources,
                   "source_updated_at": result.source_updated_at, "retrieved_at": result.retrieved_at}
            for line in ip_lines
        }
    planned[output_root / "reports/coverage.json"] = json.dumps(report, indent=2, sort_keys=True) + "\n"
    # Download, parse and validate every list before touching the previous valid release.
    for destination, content in planned.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent, delete=False) as handle:
            handle.write(content)
            temporary = Path(handle.name)
        temporary.replace(destination)
    expected_output = {destination for destination in planned
                       if destination.is_relative_to(output_root / "output")}
    for obsolete in (output_root / "output").rglob("*.txt"):
        if obsolete not in expected_output:
            obsolete.unlink()
    print(json.dumps({"lists": len(outputs), "domains": {key: len(value) for key, value in outputs.items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
