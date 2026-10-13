# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Moved the daily publication workflow, catalog renderer, and router-format
  fixtures into the generator repository. Publishing also runs when its `main`
  branch changes.
- Restricted cross-repository publication to a dedicated deploy key with write
  access only to the lists repository.
- Rebuilt both repositories from independent root commits and retired tags and
  releases that referenced the former combined history.

## [1.2.0] - 2026-10-12

### Added

- Split generator code and configuration from the separately published
  subscription lists, coverage report, router fixtures, and usage guide.
- Added an explicit output-root option so the generator writes lists and the
  coverage report directly into the lists repository.
- Added a daily workflow in the lists repository pinned to the released
  generator version.

### Changed

- Moved generated subscriptions and their source attribution into the lists
  repository; the generator repository now contains code and configuration.
- Passed the GitHub Actions token to GitHub API source requests to avoid the
  anonymous rate limit during scheduled updates.

### Known limitations

- Old Raw URLs under `marcomc/glinet-vpn-rules` do not redirect to the lists
  repository. Update configured Subscription URLs to the new repository.

## [1.1.0] - 2026-10-12

### Added

- Domain-only subscriptions for every configured provider and service, while
  preserving the original 1.0 domain URLs.
- Provider-level IPv4-only, IPv6-only, and mixed IP subscriptions for Google
  services, Microsoft 365, Telegram, Meta, Netflix, and X where attributable
  source data is available.
- Combined domain/IP subscriptions with IPv4-only, IPv6-only, and dual-stack
  variants for those providers.
- Official Google, Microsoft 365, and Telegram IP feeds, plus documented
  community ASN-based GeoIP feeds for Meta, Netflix, and X.
- CIDR normalization, validation, safe range collapsing, Google Cloud range
  subtraction, and per-range source timestamps in the coverage report.
- A validator for every published list, router-format test fixtures, and tests
  for CIDR handling, attribution, and output integrity.

### Fixed

- Excluded and reported digit-leading domains rejected by the GL.iNet
  Subscription URL parser, including the first seven entries of the original
  `google-all.txt` list.
- Updated the pinned GitHub Actions versions and made the workflow validate
  generated subscriptions before committing them.

### Known limitations

- IPv6 CIDR parsing and VPN routing still need a physical GL.iNet router test.
  IPv4-only variants are available for firmware that rejects IPv6.
- Provider-level IP ranges must not be interpreted as exclusive to a narrower
  service; Google Cloud customer and other shared hosting ranges are excluded.

## [1.0.0] - 2026-10-12

### Added

- 27 independent plain-text subscriptions: 15 Google lists and 12 other
  provider lists, each available through a GitHub Raw URL.
- A `google-all` list generated from the union of Google service lists, with
  unclassified Google domains retained in `google-other`.
- YAML configuration for providers, services, upstream sources, source
  priorities, inclusions, exclusions, output paths, and coverage notes.
- A domain generator that resolves recursive v2fly includes, detects cycles,
  normalizes hostnames, removes duplicates, and sorts output deterministically.
- Conservative conversion of supported v2fly, Clash, and MetaCubeX domain
  rules, with unsupported rules recorded in a machine-readable coverage report.
- Validation that prevents empty or malformed lists from replacing previously
  generated output after a source or generation failure.
- Daily and manually dispatched GitHub Actions updates, parser and aggregation
  tests, setup instructions, and source-license attribution.

### Known limitations

- Shared Google infrastructure can appear across service lists, and narrow
  lists may require additional Google domains for full functionality.
- Some nested domain-suffix rules may under-match when represented in the
  GL.iNet plain-text format; keyword, regex, process, and IP rules are not
  converted.
- Router compatibility is based on GL.iNet documentation and has not been
  validated on a physical GL.iNet router.
