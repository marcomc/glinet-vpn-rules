"""Resolve attributed provider CIDRs without inferring IPs from DNS."""
from __future__ import annotations

import datetime as dt
import ipaddress
import json
import os
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Union

Network = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


@dataclass(frozen=True)
class IPResult:
    networks: tuple[Network, ...]
    sources: tuple[str, ...]
    source_updated_at: dict[str, str]
    retrieved_at: str


def normalized_network(value: str) -> Network:
    if not isinstance(value, str) or "/" not in value:
        raise ValueError(f"CIDR required: {value!r}")
    network = ipaddress.ip_network(value.strip(), strict=False)
    if network.is_private or network.is_loopback or network.is_link_local or network.is_multicast:
        raise ValueError(f"non-public CIDR: {value}")
    return network


def sorted_networks(networks: set[Network] | list[Network]) -> tuple[Network, ...]:
    collapsed = ipaddress.collapse_addresses(sorted((n for n in networks if n.version == 4), key=lambda n: (int(n.network_address), n.prefixlen)))
    ipv4 = list(collapsed)
    collapsed = ipaddress.collapse_addresses(sorted((n for n in networks if n.version == 6), key=lambda n: (int(n.network_address), n.prefixlen)))
    return tuple(ipv4 + list(collapsed))


def subtract_networks(owned: tuple[Network, ...], excluded: tuple[Network, ...]) -> tuple[Network, ...]:
    remaining = list(owned)
    for blocked in excluded:
        next_remaining = []
        for network in remaining:
            if network.version != blocked.version or not network.overlaps(blocked):
                next_remaining.append(network)
            elif network.subnet_of(blocked):
                continue
            elif blocked.subnet_of(network):
                next_remaining.extend(network.address_exclude(blocked))
            else:
                raise ValueError(f"unexpected partial network overlap: {network}, {blocked}")
        remaining = next_remaining
    return sorted_networks(remaining)


def _request(url: str) -> tuple[str, dict[str, str]]:
    headers = {"User-Agent": "glinet-vpn-subscription-generator/1.0.0"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token and urllib.parse.urlparse(url).hostname == "api.github.com":
        headers["Authorization"] = f"Bearer {token}"
        headers["Accept"] = "application/vnd.github+json"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=35) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        content = response.read(4_000_001).decode("utf-8-sig")
        return content, dict(response.headers)


def _json(url: str):
    body, headers = _request(url)
    return json.loads(body), headers


def _google_prefixes(document: dict) -> tuple[Network, ...]:
    if not isinstance(document, dict) or not isinstance(document.get("prefixes"), list) or not document["prefixes"]:
        raise ValueError("invalid Google prefix document")
    networks = []
    for item in document["prefixes"]:
        if not isinstance(item, dict):
            raise ValueError("invalid Google prefix entry")
        value = item.get("ipv4Prefix") or item.get("ipv6Prefix")
        networks.append(normalized_network(value))
    return sorted_networks(networks)


def _http_updated(headers: dict[str, str], retrieved_at: str) -> str:
    last_modified = headers.get("Last-Modified") or headers.get("last-modified")
    if last_modified:
        return parsedate_to_datetime(last_modified).astimezone(dt.timezone.utc).isoformat()
    return retrieved_at


def resolve_ip_source(spec: dict, retrieved_at: str) -> IPResult:
    kind = spec["format"]
    if kind == "google-services":
        owned, _ = _json(spec["url"])
        cloud, _ = _json(spec["exclude_url"])
        if not owned.get("creationTime") or not cloud.get("creationTime"):
            raise ValueError("Google source timestamps missing")
        networks = subtract_networks(_google_prefixes(owned), _google_prefixes(cloud))
        stamps = {spec["url"]: owned["creationTime"], spec["exclude_url"]: cloud["creationTime"]}
        sources = (spec["url"], spec["exclude_url"])
    elif kind == "microsoft-365":
        query = urllib.parse.urlencode({"ClientRequestId": str(uuid.uuid4())})
        records, _ = _json(spec["url"] + "?" + query)
        version, _ = _json(spec["version_url"] + "?" + query)
        if not isinstance(records, list) or not isinstance(version, dict) or not version.get("latest"):
            raise ValueError("invalid Microsoft 365 feed")
        networks = sorted_networks([normalized_network(value) for row in records for value in row.get("ips", [])])
        stamp = str(version["latest"])
        if len(stamp) < 8 or not stamp[:8].isdigit():
            raise ValueError("invalid Microsoft 365 feed version")
        sources = (spec["url"], spec["version_url"])
        stamps = {spec["url"]: f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]} (version {stamp})", spec["version_url"]: stamp}
    elif kind in {"cidr-lines", "community-cidr"}:
        body, headers = _request(spec["url"])
        values = [line.strip() for line in body.splitlines() if line.strip() and not line.lstrip().startswith("#")]
        networks = sorted_networks([normalized_network(value) for value in values])
        if kind == "community-cidr":
            metadata, _ = _json(spec["commit_url"])
            if not isinstance(metadata, list) or not metadata or not metadata[0].get("commit", {}).get("committer", {}).get("date"):
                raise ValueError("community source commit timestamp missing")
            updated = metadata[0]["commit"]["committer"]["date"]
            sources = (spec["url"], spec["commit_url"])
            stamps = {spec["url"]: updated, spec["commit_url"]: updated}
        else:
            sources = (spec["url"],)
            stamps = {spec["url"]: _http_updated(headers, retrieved_at)}
    else:
        raise ValueError(f"unsupported IP source format: {kind}")
    if not networks:
        raise ValueError(f"empty IP source: {spec['url']}")
    return IPResult(networks, sources, stamps, retrieved_at)
