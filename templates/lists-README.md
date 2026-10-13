# GL.iNet VPN subscription lists

Public domain and IP routing subscriptions for the GL.iNet VPN client Subscription URL feature. The [generator repository](https://github.com/marcomc/glinet-vpn-subscription-generator) contains the source code, configuration, tests, and publication workflow. This repository publishes only the generated files, [coverage report](reports/coverage.json), and usage and licensing metadata.

Other OpenWrt VPN clients can use these lists when their policy importer accepts the same one-rule-per-line domain and CIDR syntax.

## Contents

- [Choose a subscription](#choose-a-subscription)
- [Subscription URLs](#subscription-urls)
- [Migration](#migration)
- [Compatibility and limitations](#compatibility-and-limitations)
- [Updates and attribution](#updates-and-attribution)

## Choose a subscription

Choose a file listed under [`output/`](output/), then use its Raw URL. For example, `google/google-all-domains.txt` is a domain-only Google subscription.

| Suffix | Contents | Use |
| --- | --- | --- |
| `-domains.txt` | Domains | Most broadly documented GL.iNet subscription format |
| `-ips-v4.txt` | IPv4 CIDRs | IPv4-only IP routing |
| `-ips-v6.txt` | IPv6 CIDRs | Use only after testing IPv6 import and routing on your firmware |
| `-ips.txt` | IPv4 and IPv6 CIDRs | Use when both address families are supported |
| `-combined-v4.txt` | Domains and IPv4 CIDRs | Use when the importer accepts mixed rules |
| `-combined-v6.txt` | Domains and IPv6 CIDRs | Use after testing mixed rules and IPv6 routing |
| `-combined.txt` | Domains and available CIDRs | Use after testing mixed rules and both address families |

IP variants exist only where an attributable provider-specific source is available. A provider-level IP range may serve several services and does not imply exclusive ownership by one service.

## Subscription URLs

Use the **Raw** URL of the desired file in the GL.iNet VPN client's Subscription URL field. The table is regenerated from the coverage report with each list update.

In the GL.iNet VPN dashboard, edit or create a VPN policy, select **Specified
Domain / IP List**, choose **Subscription URL**, and paste a Raw URL from the
table. Select **Detect** and confirm that no lines fail, then apply the policy
and test traffic through the intended VPN tunnel. Use a `-combined-v4.txt` list
when the tunnel has no IPv6 route.

<!-- BEGIN GENERATED CATALOG -->

<!-- END GENERATED CATALOG -->

Provider directories currently include Amazon, Anthropic, Apple, Cloudflare, Google, Meta, Microsoft, Netflix, OpenAI, Spotify, Telegram, TikTok, and X. Google service labels cover core services and accounts, APIs and Firebase, Gmail, YouTube, Drive, Docs, Maps, Photos, Meet, Cloud, Ads, Play, and Gemini; `other` holds unclassified Google domains, and `all` is their union. Check [coverage](reports/coverage.json) for source attribution and limitations.

## Migration

The former `marcomc/glinet-vpn-rules` repository was renamed to the generator and its generated output was moved here. Existing URLs such as `https://raw.githubusercontent.com/marcomc/glinet-vpn-rules/main/output/google/google-all.txt` return HTTP 404. Replace the repository name in each configured Subscription URL with `glinet-vpn-subscription-lists`, then choose the desired variant above. A GitHub repository redirect does not keep the old Raw URLs working.

Combined lists now use `-combined.txt`, `-combined-v4.txt`, and `-combined-v6.txt` instead of `-all.txt`, `-all-v4.txt`, and `-all-v6.txt`. Plain `<name>.txt` domain aliases are removed; use `<name>-domains.txt`. Update any saved Subscription URLs to the canonical filename.

## Compatibility and limitations

- GL.iNet documents domain and IPv4 CIDR subscriptions. Firmware support for IPv6 CIDRs and mixing domains with CIDRs must be verified on the target router. The [generator's router-format fixtures](https://github.com/marcomc/glinet-vpn-subscription-generator/tree/main/tests/fixtures/router) provide small import tests for IPv4, IPv6, and mixed syntax.
- After import, check the detected rule count and route real IPv4 and IPv6 traffic through the intended VPN tunnel. A successful import alone does not prove routing.
- Encrypted or external DNS, direct IP connections, and IPv6 paths outside the VPN policy can bypass domain-based policies.
- Shared cloud allocations and DNS-derived IP addresses are excluded from provider IP lists. See [source attribution](DATA-LICENSES.md) and the coverage report for provenance and update timestamps.
- OpenAI currently has a domain list only. Its published crawler and integration CIDRs describe OpenAI-originated connections, so they are unsuitable as ChatGPT client destinations. Microsoft 365's official endpoint feed supplements Microsoft domains and IPs but does not cover every Microsoft product.
- Provider and community feeds can omit changing regional endpoints or third-party dependencies; use the coverage report to inspect each list's source scope.

## Updates and attribution

Only the [generator workflow](https://github.com/marcomc/glinet-vpn-subscription-generator/blob/main/.github/workflows/update-lists.yml) publishes updates here. It runs when the generator's `main` branch changes, daily at 03:17 UTC, or on manual dispatch; new upstream data never changes the generator repository. See [license scope](LICENSE) and [data sources and licenses](DATA-LICENSES.md). The router's own automatic subscription refresh depends on its firmware and has not been verified.
