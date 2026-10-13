# GL.iNet VPN subscription generator

This repository contains the source code and configuration that generate plain-text domain and IP routing subscriptions for the GL.iNet VPN client Subscription URL feature. Generated subscriptions are published separately in [glinet-vpn-subscription-lists](https://github.com/marcomc/glinet-vpn-subscription-lists).

Other OpenWrt VPN clients can use the published lists only when their policy importer accepts the same one-rule-per-line domain and CIDR syntax.

## Contents

- [Repositories](#repositories)
- [Generate and validate lists](#generate-and-validate-lists)
- [Development](#development)
- [Compatibility and data limitations](#compatibility-and-data-limitations)
- [Publication](#publication)

## Repositories

| Repository | Contents |
| --- | --- |
| [glinet-vpn-subscription-generator](https://github.com/marcomc/glinet-vpn-subscription-generator) | Generator, source configuration, tests, router-format fixtures, and publication workflow |
| [glinet-vpn-subscription-lists](https://github.com/marcomc/glinet-vpn-subscription-lists) | Published domain/IP lists, coverage report, and subscription guide |

See the lists repository README for subscription URLs, setup steps, source attribution, and current coverage.

## Generate and validate lists

Clone both repositories as sibling directories, install the Python dependencies, then run the generator with the lists repository as its output root:

```sh
python -m pip install -r requirements.txt
python scripts/generate.py --output-root ../glinet-vpn-subscription-lists
python scripts/validate.py --root ../glinet-vpn-subscription-lists
python scripts/render_catalog.py --root ../glinet-vpn-subscription-lists
```

The output root is required so generated files are not written into the generator repository by mistake. Generation downloads configured upstream sources and writes the lists and `reports/coverage.json` only after all sources have been fetched and parsed. It removes obsolete generated list files, including the former plain-name and `-all` format aliases. The published README is rendered from [`templates/lists-README.md`](templates/lists-README.md).

## Development

The YAML configuration in [`config/services.yml`](config/services.yml) defines domain and attributable IP sources, provider/service mappings, and coverage notes. The generator resolves recursive includes, normalizes domains and CIDRs, removes duplicates, safely collapses overlapping ranges within a provider source, and sorts output deterministically.

Run the offline unit suite with:

```sh
python -m unittest discover -s tests -v
```

## Compatibility and data limitations

- Lists target the GL.iNet VPN client Subscription URL feature. GL.iNet documents domain and IPv4 CIDR rules; IPv6 parsing and routing vary by firmware and should be tested on the target router. IPv4-only links remain available.
- Other OpenWrt clients do not share one standard subscription parser. Confirm that the specific client accepts the list syntax before use.
- The generator filters domains known to be rejected by the GL.iNet parser and validates every generated list before publication.
- IP ranges are published only when source attribution is available. Shared cloud allocations and DNS-derived IP addresses are excluded; provider-level IP lists do not imply service-exclusive ownership.
- Domain policies can be bypassed by external or encrypted DNS, direct IP connections, or IPv6 paths not routed through the VPN. A successful import does not prove traffic is routed through the selected tunnel.

Source licensing and attribution for generated data are documented in [the lists repository](https://github.com/marcomc/glinet-vpn-subscription-lists/blob/main/DATA-LICENSES.md).

## Publication

The [publication workflow](.github/workflows/update-lists.yml) runs on changes to `main`, daily at 03:17 UTC, and on manual dispatch. It tests the generator, builds and validates the subscriptions, refreshes the catalog, then commits the result to the lists repository. A repository-specific deploy key grants this workflow write access only to the lists repository. Changes to source configuration or generator code are made here by maintainers. New upstream data updates only the lists repository; the workflow never commits to or updates the generator itself. The published Raw URLs stay stable.
