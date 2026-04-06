---
name: human-review-handoff
description: |
  Generates a structured, human-readable reviewer packet summarising what changed in a pull request, why it matters, what was verified, and where human attention is most needed. Use when the user asks for a PR review summary, a code review packet, a human-readable change report, or wants to hand off review findings to a human reviewer. Produces a scannable document: quick approvals (low-risk PRs) can be assessed in under 30 seconds; detailed reviews (high-risk PRs) in under 2 minutes. Outputs a formatted markdown packet with risk rating, verification status, ranked findings, unresolved questions, and a recommended review focus — making human review faster without replacing human judgment.
---

# Human Review Handoff

Build the final reviewer packet that a human reviewer actually reads.

## When to use and inputs

After `finding-synthesizer` has produced the ranked finding set — always for medium/high-risk PRs, and for low-risk PRs when findings exist. Consumes synthesized findings from `finding-synthesizer` and the evidence pack from `pr-evidence-builder`.

## Steps

1. **Build the reviewer packet** using the packet structure below.

### Packet structure

The packet contains these sections (see the example output for exact formatting):

- **TL;DR** — 1–2 sentence summary: what changed, risk lane, top concern if any
- **Risk** — LOW / MEDIUM / HIGH with contributing factors and AI-assisted flag
- **Verification Status** — table: verifier name | status | notable findings
- **Findings** — ordered by severity × confidence; each entry includes title, file:line, why it matters, evidence type/source, and suggested action (fix | verify | discuss)
- **Unresolved Assumptions** — things the review couldn't determine; questions for the human
- **Recommended Review Focus** — specific files/hunks where human attention is most needed and why
- **Metadata** — reviewer mode, reviewer model family, authoring model family (if detected), wall-clock time, context isolation

### Example output (abbreviated)

```markdown
## PR Review Packet

### TL;DR
Adds OAuth2 token refresh logic to `auth/session.py`; risk is MEDIUM due to
token-expiry edge cases. One unresolved assumption about clock-skew tolerance
requires human input.

### Risk: MEDIUM
Contributing factors:
- Modifies authentication flow (high-impact surface)
- No new tests for the refresh-failure path
AI-assisted: yes (GitHub Copilot detected in commit metadata)

### Verification Status
| Verifier          | Status  | Notable Findings                        |
|-------------------|---------|-----------------------------------------|
| Static analysis   | PASS    | No new lint errors                      |
| Test coverage     | WARN    | refresh-failure branch uncovered (0%)   |
| Dependency audit  | PASS    | No new vulnerable packages              |

### Findings (2 items)
1. **Uncovered refresh-failure branch** — `auth/session.py:114`
   Why it matters: Silent failure on token refresh could leave users with
   expired sessions and no error feedback.
   Evidence: Coverage report (pr-evidence-builder)
   Suggested action: fix

2. **Clock-skew tolerance undocumented** — `auth/session.py:87`
   Why it matters: Token expiry comparison assumes clocks are in sync; distributed
   deployments may reject valid tokens prematurely.
   Evidence: Code inspection (finding-synthesizer)
   Suggested action: discuss

### Unresolved Assumptions
- What is the acceptable clock-skew window for this deployment environment?

### Recommended Review Focus
- `auth/session.py` lines 87–120: expiry logic and the uncovered failure branch
  are the highest-risk hunks; verify behaviour under clock drift and network
  timeout conditions.

### Metadata
- reviewer mode: fresh_eyes
- reviewer model family: claude-3
- authoring model family: unknown
- wall-clock time: 47 s
- context isolation: yes

---
*This is an evidence-based review aid, not an approval. The tile produces
findings and questions. Humans produce decisions.*
```

2. **Add the review-boundaries disclaimer.** Every packet must include: "This is an evidence-based review aid, not an approval. The tile produces findings and questions. Humans produce decisions."

3. **Mark escalation areas.** If any human-escalation triggers are present, surface specific questions the human reviewer should answer.

4. **Validate the packet** before delivering it. Run through this checklist:

   - [ ] TL;DR is present and ≤ 2 sentences
   - [ ] Risk rating is one of LOW / MEDIUM / HIGH with contributing factors listed
   - [ ] Verification Status table is populated (or explicitly marked "no verifiers run")
   - [ ] Findings are ordered by severity × confidence and each has a suggested action
   - [ ] Unresolved Assumptions section is present (may be empty — explicitly state "None")
   - [ ] Recommended Review Focus names specific files or hunks
   - [ ] Review-boundaries disclaimer is included verbatim
   - [ ] Metadata block is complete

   If any item is missing, regenerate or patch that section before handing off.

## Related skills

- **`finding-synthesizer`** — produces the ranked finding set consumed by this skill
- **`pr-evidence-builder`** — produces the evidence pack consumed by this skill
