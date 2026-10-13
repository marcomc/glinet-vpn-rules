# Contributing

Thanks for helping improve the GL.iNet VPN subscription lists. Changes to source data, parsing, and validation belong in this generator repository. The [published lists](https://github.com/marcomc/glinet-vpn-subscription-lists) are generated output.

## Report a problem or request a source

Use a [list problem](https://github.com/marcomc/glinet-vpn-subscription-generator/issues/new?template=list_problem.md) report for invalid rules, wrong attribution, missing destinations, or router import errors. Use a [source request](https://github.com/marcomc/glinet-vpn-subscription-generator/issues/new?template=source_request.md) for a new provider or feed.

Include the affected subscription URL, firmware version when relevant, the observed failure, and a public source for the proposed rules. Do not post router credentials, VPN keys, or private addresses.

## Source requirements

- Prefer official provider publications that describe **destination** domains or IP ranges. A provider's crawler or integration egress IPs are not VPN client destinations.
- For community-maintained feeds, link to the source, explain its update history and attribution scope, and note any applicable license.
- Do not infer IP allocations from DNS answers or assign shared cloud/CDN infrastructure exclusively to a service.
- Keep IPv4 and IPv6 CIDRs valid and preserve source URLs and update timestamps in the generated coverage report.
- Describe what the source does **not** cover. Dynamic regional endpoints and third-party dependencies can change.

## Make a change

Clone the generator and lists repositories as sibling directories, then run:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/generate.py --output-root ../glinet-vpn-subscription-lists
python scripts/validate.py --root ../glinet-vpn-subscription-lists
python scripts/render_catalog.py --root ../glinet-vpn-subscription-lists
```

Update [`config/services.yml`](config/services.yml) for a source or provider change. Add a focused test when parsing or validation behavior changes. In the pull request, link the upstream source and summarize the generated list and coverage changes. The maintainer's workflow publishes accepted changes to the lists repository.
