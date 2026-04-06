# Evidence Threshold

Every surfaced finding must be backed by concrete evidence. The evidence threshold is the volume control — not an arbitrary cap.

## A surfaced finding must include at least one of

- Deterministic verifier output (test failure, lint error, type error, security scan hit)
- Concrete hunk-level code evidence (specific line, specific problem, specific consequence)
- Repo-instruction or policy conflict (citable rule from repo config, CODEOWNERS, or contributing guide)
- Explicit contextual reasoning tied to changed code (cross-reference with existing code that creates the problem)

## Handling findings that don't meet this bar

- Low confidence with no concrete reasoning: suppress entirely
- Never surface a finding whose only evidence is "this looks like it might be wrong"

## Do not over-hedge

If you can trace a concrete problem through the code (e.g., data flows from user input to a query, a cache stores authorization state that can become stale, a check-then-act sequence has a gap), that IS concrete evidence — it is "explicit contextual reasoning tied to changed code." State it as a finding with the confidence you actually have. Do not downgrade clear reasoning-based findings to questions just because no verifier flagged them. The point of the evidence threshold is to filter out vague intuition, not to penalize careful code reading.

## Infrastructure configuration IS concrete evidence

A Terraform resource with `backup_retention_period = 0`, a replica pinned to the same AZ as its primary, or a storage lifecycle rule that transitions objects to a tier with hours-long retrieval — these are concrete, hunk-level code evidence with specific, measurable consequences. Do not suppress infrastructure configuration findings as "standard practice," "default value," or "out of scope." If the configuration is in the diff and has a plausible operational impact, it clears the evidence threshold.

Infrastructure findings are often **multi-part** — do not stop at the first issue. A replica resource may have both a same-AZ placement problem AND a backup retention problem AND an engine change that triggers destroy-and-recreate. Each is a separate finding with independent impact. Surface all of them.

## Evidence type disclosure

Every surfaced finding must include its evidence type so the human reviewer can assess trust calibration.
