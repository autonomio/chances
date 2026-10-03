# Maintainers

Current maintainer:

- Mikko Kotila

Maintainers own release approval, security advisory triage, issue prioritization, and merge decisions for this repository.

`bit-mis` is the approving authority named in [CLAUDE.md](CLAUDE.md) and
`governance.yml`; activation must verify their repository write access.
After `.github/CODEOWNERS` is merged, its sole global owner and required code-owner
review make `bit-mis`'s approval mandatory for every PR. Approval count alone does
not select a login. PR authors cannot approve their own PR; the most recent
reviewable push also needs approval from someone other than its pusher.
See [SETUP.md](SETUP.md) for review and release environment activation.

## Continuity evidence

Repository access checked on 2026-10-03: `mikkokotila` and `EnergyGuy3` have
administrator access; `bit-mis` has write access. These permissions establish
access, not succession authority. Releases publish automatically after reviewed
merges; deployment adds no reviewer.

The proposed recovery owner is `EnergyGuy3`, with a one-week recovery deadline
from confirmation that the maintainer or approving authority cannot respond.
Maintainer confirmation of legal authority, organization credential recovery,
and an authorized replacement-review procedure is pending. This proposal does
not activate replacement authority or permit bypassing current protections.

Before claiming continuity, document the authorized recovery steps and verify
that they can restore issue administration, protected change approval and
publication within that deadline. Preserve `bit-mis` as the normal approving
authority and automatic release as the normal publication path.
See the [assurance case](docs/Developer/Security-Assurance-Case.md) for the
remaining Silver evidence.
