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

Proposed recovery sequence, subject to that confirmation:

1. Record the confirmed absence, recovery owner and one-week deadline in a
   public incident issue; keep credentials and private security reports private.
2. Verify the recovery owner's repository and organization administration,
   issue access, and ability to restore the release credentials through the
   organization secret store. Never copy secret values into the incident.
3. Restore protected change approval. If `bit-mis` is unavailable, an explicitly
   authorized emergency succession policy must already permit replacement of
   the sole code owner. Current rules do not provide that policy: another admin
   alone cannot satisfy mandatory approval. Establish it through a separate
   reviewed governance slice while the current authority remains available.
4. Run the required checks on the recovered branch, obtain the authorized
   review and merge through branch protection. Verify automatic release,
   publication and downloadable signatures against the approved source.
5. Record the restored capabilities and elapsed recovery time in the incident.

Until succession authority and a viable approval-recovery procedure are
established, the access-continuity criterion remains unknown. Normal approval
stays with `bit-mis`; release remains automatic.
See the [assurance case](docs/Developer/Security-Assurance-Case.md) for the
remaining Silver evidence.
