# Source audit for 1.1.0

Checked 2026-10-13. This audit covers the providers currently configured in
`config/services.yml` and the additional domains and CIDRs in the supplied
OpenAI text file. It distinguishes addresses a VPN client connects to
(destination rules) from addresses operated by a provider to connect outward
(egress rules). The pasted values are observations, not proof of ownership or
service attribution.

## Findings

There is no authoritative, regularly updated feed that provides a complete
destination-domain and destination-IP inventory for every configured provider.
“Complete” cannot be promised for dynamic services: providers use shared CDNs,
regional edges, third-party identity, telemetry, payment, and storage services,
and many publish only product-specific network requirements.

Use official, scoped endpoint feeds when they describe client destinations.
Use maintained community domain and GeoIP data only with explicit provenance
and coverage caveats. Do not infer provider ranges from DNS answers or treat a
cloud/CDN operator's whole network as belonging to a hosted application.

## OpenAI

| Source or observation | What it establishes | Safe use |
| --- | --- | --- |
| [OpenAI network recommendations](https://help.openai.com/en/articles/9247338-network-recommendations-for-chatgpt-errors-on-web-and-apps) | Official network troubleshooting reference for ChatGPT web and apps; this page returned HTTP 403 to the research fetcher, so its current host list could not be independently extracted here. | Review the current page manually and use only its documented client destination hostnames. It is not an IP range feed. |
| [v2fly OpenAI domain data](https://raw.githubusercontent.com/v2fly/domain-list-community/master/data/openai) | Maintained community domain rules; it includes first-party names and service/CDN dependencies, with community curation rather than an OpenAI completeness guarantee. | Add as a second domain source, then audit dependency domains and preserve its attribution. It improves coverage but cannot establish completeness. |
| [Blackmatrix7 OpenAI rules](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/OpenAI/OpenAI.list) | Community rules currently include domains, two `/32` CIDRs, and ASN 20473. The existing generator parses only domain rules, so it drops the IP and ASN records. | Keep domain rules subject to review. Exclude the two IPs and ASN from service CIDRs: the file does not establish that these shared-hosting addresses are dedicated OpenAI destinations. |
| [OpenAI `chatgpt-user.json`](https://openai.com/chatgpt-user.json), [`chatgpt-actions.json`](https://openai.com/chatgpt-actions.json), [`chatgpt-connectors.json`](https://openai.com/chatgpt-connectors.json), [`chatgpt-voice.json`](https://openai.com/chatgpt-voice.json), [`gptbot.json`](https://openai.com/gptbot.json), and [`searchbot.json`](https://openai.com/searchbot.json) | Official, timestamped prefix documents for named ChatGPT actors, integrations, or crawlers. They describe OpenAI-originated traffic toward other systems. The crawler files explicitly identify crawler actors. | **Do not publish these as client-to-OpenAI VPN destination CIDRs.** They are the wrong traffic direction and could reroute or capture unrelated traffic. They are useful to operators firewalling their own inbound services against the named OpenAI caller. |
| Pasted hostnames such as `ifconfig.me`, `auth0.com`, `workos.com`, `stripe.com`, `intercom.io`, `sentry.io`, and analytics/CDN names | A hostname observation does not prove it is required, exclusive to OpenAI, or safe as a whole domain suffix. `ifconfig.me` is a public diagnostic endpoint, not an OpenAI service. | Do not add these wholesale. Add an exact third-party hostname only when current OpenAI documentation establishes the dependency and the broad rule will not capture unrelated sites. Never convert the pasted resolved IPs into durable ranges. |

**OpenAI result:** Adding V2Fly's current domain dataset is a defensible coverage improvement; combine it with reviewed first-party names from the official network guide. No official OpenAI feed found here publishes IP ranges that represent ChatGPT/API client destinations. The official JSON feeds in the pasted file are egress allowlist data, not destination subscriptions.

## Current providers and strongest usable sources

| Provider in configuration | Current source coverage | Official source and safe scope | Gaps / exclusions |
| --- | --- | --- | --- |
| Google | V2Fly, Blackmatrix7, MetaCubeX, curated domains; `goog.json` with `cloud.json` subtraction for IPs. | [Google published service prefixes](https://www.gstatic.com/ipranges/goog.json) and [Google Cloud prefixes](https://www.gstatic.com/ipranges/cloud.json) are regularly timestamped. Excluding Cloud prefixes avoids broad Google Cloud customer allocations. The remainder is still shared Google service/edge infrastructure and is safe only as a broad Google-provider policy, not service attribution. | No complete official domain feed for all Google consumer products was identified. Workspace IP/domain help pages are scoped to Workspace operations and should not be represented as all Google. Do not claim the remainder of `goog.json` is exclusive to a particular Google service. |
| Apple | V2Fly and Blackmatrix7 domains; no IP source. | [Apple enterprise network requirements](https://support.apple.com/101555) documents product network destinations and is a potential source for explicit Apple domain rules. | Product-specific requirements are not a complete Apple domain inventory. No general destination CIDR feed was identified. iCloud Private Relay egress prefixes, if considered, are relay exit addresses, not Apple destinations for a VPN client. |
| Microsoft | V2Fly and Blackmatrix7 domains; Microsoft 365 endpoint feed for IPs. | [Microsoft 365 Worldwide endpoints API](https://endpoints.office.com/endpoints/worldwide) and its [version endpoint](https://endpoints.office.com/version/worldwide) provide dated, scoped Microsoft 365 URLs and IPs. Keep service areas/category metadata when filtering. | This covers Microsoft 365 endpoint requirements, not every Microsoft service. Do not append all Azure service-tag or Azure `ServiceTags_Public` ranges: those include broad cloud infrastructure and customer workloads. |
| OpenAI | Blackmatrix7 domains only; community rule's CIDR/ASN entries are ignored by the current parser. | Use reviewed OpenAI client-domain documentation and V2Fly OpenAI domains as above. | No official client-destination CIDR feed identified. Official OpenAI actor JSONs are egress and must not be used as destination ranges. |
| Meta (Facebook/Instagram) | V2Fly and Blackmatrix7 domains; community `Loyalsoldier/geoip` Facebook prefixes. | [Loyalsoldier Facebook GeoIP list](https://raw.githubusercontent.com/Loyalsoldier/geoip/release/text/facebook.txt), with its [commit metadata](https://api.github.com/repos/Loyalsoldier/geoip/commits?path=text/facebook.txt&sha=release&per_page=1), is a maintained, attributed community classification. It can support a broad Meta-owned-network policy if its ASN-based scope is accepted. | No official service-specific Meta destination CIDR feed identified. GeoIP classification is neither a completeness guarantee nor a separation of Facebook, Instagram, and shared Meta infrastructure. |
| Amazon (including AWS in current config) | V2Fly Amazon/AWS domains and Blackmatrix7 Amazon domains; no IP source. | [AWS `ip-ranges.json`](https://ip-ranges.amazonaws.com/ip-ranges.json) is official and timestamped for AWS infrastructure by service/region. | AWS ranges host unrelated customer workloads; exclude the whole feed from an Amazon/AWS destination subscription. The current single `amazon-all` combines retail Amazon with AWS; that is a scope/attribution gap and should be split before claiming “all Amazon.” No general retail Amazon destination CIDR feed identified. |
| Netflix | V2Fly and Blackmatrix7 domains; community `Loyalsoldier/geoip` Netflix prefixes. | [Loyalsoldier Netflix GeoIP list](https://raw.githubusercontent.com/Loyalsoldier/geoip/release/text/netflix.txt) and [commit metadata](https://api.github.com/repos/Loyalsoldier/geoip/commits?path=text/netflix.txt&sha=release&per_page=1) provide maintained community attribution. | No general official client-destination CIDR feed identified. Open Connect material is about Netflix content delivery and ISP deployments; it is not a complete consumer destination feed. Community IP ranges may miss delivery through partner networks. |
| Spotify | Blackmatrix7 domains; no IP source. | [Spotify Connect networking guidance](https://support.spotify.com/article/spotify-connect/) is product-specific operational documentation, not an IP feed. | No authoritative general Spotify destination CIDR/domain feed identified. Keep community domain coverage explicitly non-exhaustive. |
| Cloudflare | V2Fly and Blackmatrix7 domains; no IP source. | Cloudflare's official [IPv4](https://www.cloudflare.com/ips-v4/) and [IPv6](https://www.cloudflare.com/ips-v6/) files are current and authoritative for Cloudflare's network. | **Exclude these prefixes from a Cloudflare service list:** Cloudflare proxies customer websites and shared services on these anycast networks. Including them routes unrelated third-party destinations. Prefer exact Cloudflare product hostnames from the relevant official product documentation; no single universal service destination IP feed identified. |
| Anthropic | V2Fly and Blackmatrix7 domains; no IP source. | [Anthropic API overview](https://docs.anthropic.com/en/api/overview) identifies the API service and its documented client endpoint. Use official client hostnames where documented. | No general official destination CIDR feed identified. Anthropic API IP-allowlisting material, where applicable, concerns customer source IPs allowed to call Anthropic and is not an Anthropic destination prefix list. |
| X (Twitter) | Blackmatrix7 domains; community `Loyalsoldier/geoip` Twitter prefixes. | [Loyalsoldier Twitter GeoIP list](https://raw.githubusercontent.com/Loyalsoldier/geoip/release/text/twitter.txt) and [commit metadata](https://api.github.com/repos/Loyalsoldier/geoip/commits?path=text/twitter.txt&sha=release&per_page=1) provide maintained community attribution. | No official general client-destination CIDR feed identified. IP attribution is broad network/provider scope and does not establish service-exclusive use or complete coverage. |
| Telegram | Blackmatrix7 domains plus community domains; official `cidr.txt` IP source. | [Telegram's CIDR file](https://core.telegram.org/resources/cidr.txt) is an official destination candidate for Telegram infrastructure. | The fetched response had `Last-Modified: 2021-10-01`; it is not regularly refreshed by HTTP metadata and should be treated as stale until Telegram confirms currentness. It may describe data-center/MTProto transport only, not every Telegram feature. Do not call it complete. |
| TikTok | Blackmatrix7 domains; no IP source. | No general official client-destination feed identified. Official product/advertising allowlists are scoped to their documented product and should be considered only for that use. | Community domain rules are non-exhaustive; no attributable, regularly updated destination CIDRs found. |

## Handling the supplied OpenAI IP observations

The pasted file combines hostnames with different ownerships and purposes, and
CIDRs at `/32` or `/128` granularity alongside broader blocks. The OpenAI JSON
filenames identify several of the blocks as OpenAI-originated caller/crawler
addresses. A destination VPN list cannot use those to represent servers that a
ChatGPT client connects to. Treat every other pasted CIDR as unattributed unless
it can be matched to a documented destination feed; an address observed while
resolving a hostname is not durable ownership evidence. In particular:

- Exclude OpenAI crawler, SearchBot, ChatGPT user, Actions, Connectors, and
  Voice egress prefixes from client destination rules.
- Exclude Cloudflare, Azure, AWS, and other shared hosting/CDN prefixes unless
  the source explicitly labels a product-dedicated client destination range.
- Do not include a third-party provider's entire suffix (for example,
  `stripe.com` or `auth0.com`) based solely on an observed OpenAI request.
- Keep exact third-party host dependencies only when an official current
  network-requirements source establishes them; document that the hostname is
  a third-party dependency rather than OpenAI-owned infrastructure.
- Do not infer IP ranges from DNS, browser observations, or individual pasted
  `/32` and `/128` values.

## Release 1.1.0 source plan

1. Add V2Fly `data/openai` as a supplemental OpenAI **domain** source and retain
   Blackmatrix7 as a community source; record that this expands coverage but
   does not make it complete.
2. Review the official OpenAI network-recommendations page for first-party
   client destinations and add only specific documented hostnames that pass
   the generator's syntax rules.
3. Do not add OpenAI IP sources unless OpenAI publishes a feed explicitly
   describing destination ranges for ChatGPT/API clients.
4. Improve other providers only with scoped official endpoint feeds or
   attributed community sources that have a clear provider-network rationale.
   Keep AWS, Cloudflare, Azure, and other multi-tenant allocations out of
   service-specific lists.
5. Make completeness claims only for the scope of a feed (for example,
   Microsoft 365 worldwide endpoint categories), never for a provider's entire
   product universe unless its official source says that is what it covers.

## Source limitations

This audit is a source assessment, not evidence that every published list will
route all traffic for a provider. Official and community source contents change;
re-check their semantics and timestamps during implementation. Several official
help pages are scoped to specific apps, regions, or enterprise firewall use.
Service domains can resolve to shared anycast/CDN IPs, and third-party
dependencies can change without notice.
