# Pull request

## Change

Describe the provider, source, parser, or documentation change.

## Source and scope

- Upstream URL and applicable license or attribution:
- Destination rules covered and known gaps:
- For CIDRs, evidence that they belong to the provider rather than shared hosting:

## Validation

- [ ] Offline tests pass: `python -m unittest discover -s tests -v`
- [ ] Generated lists pass, if source data or parsing changed: `python scripts/validate.py --root ../glinet-vpn-subscription-lists`
- [ ] The affected router import or routing behavior was checked, if applicable
