# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-13

### Added

- Configurable generation of domain subscriptions for 27 provider and service
  selections, including aggregated Google service rules.
- Domain parsing from v2fly, Clash, and MetaCubeX sources, with normalization,
  deduplication, deterministic ordering, and filtering of rules rejected by the
  GL.iNet Subscription URL parser.
- Attributable IPv4 and IPv6 CIDR subscriptions from official Google,
  Microsoft 365, and Telegram sources and documented community GeoIP sources
  for Meta, Netflix, and X. Shared Google Cloud customer ranges are excluded.
- CIDR validation, normalization, safe collapsing, and per-range source and
  update timestamps in a machine-readable coverage report.
- Canonical `-domains`, `-ips-v4`, `-ips-v6`, `-ips`, `-combined-v4`,
  `-combined-v6`, and `-combined` list formats where reliable data exists.
- Validation and offline tests for generated rules, aggregation, source
  attribution, CIDR syntax, and output integrity.
- Automated publication to the separate lists repository after generator
  changes, daily, or by manual dispatch, using a dedicated deploy key.
- Generated subscription catalog, source-license attribution, and GL.iNet VPN
  client compatibility guidance in the published lists repository.
