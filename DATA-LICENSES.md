# Data sources and licenses

Generated subscriptions contain domain facts and selections derived from:

- [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community), MIT.
- [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script), GPL-2.0.
- [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat), GPL-3.0.
- [Microsoft 365 IP Address and URL web service](https://learn.microsoft.com/en-us/microsoft-365/enterprise/microsoft-365-ip-web-service?view=o365-worldwide), for official Microsoft 365 URL patterns.

IP subscriptions use these published sources:

- [Google `goog.json` and `cloud.json`](https://cloud.google.com/vpc/docs/configure-private-google-access), with Google Cloud ranges subtracted.
- [Microsoft 365 IP Address and URL web service](https://learn.microsoft.com/en-us/microsoft-365/enterprise/microsoft-365-ip-web-service?view=o365-worldwide).
- [Telegram CIDR list](https://core.telegram.org/resources/cidr.txt).
- [Loyalsoldier/geoip](https://github.com/Loyalsoldier/geoip), CC-BY-SA-4.0, for the Meta, Netflix, and X provider ASN categories.

See each upstream project for complete license terms and attribution.
The MIT license in this repository covers only original generator code and
repository documentation; it does not relicense upstream data or generated
lists. Each emitted range and its source timestamp are recorded in
[reports/coverage.json](reports/coverage.json).
