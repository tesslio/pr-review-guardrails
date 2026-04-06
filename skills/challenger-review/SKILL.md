---
name: challenger-review
description: |
  Stress-test the primary review with an additional independent reviewer that generates its own findings,
  compares reviewer conclusions, and identifies issues the primary reviewer may have missed.
  Use when performing a second opinion or double-check review on a pull request, for medium or high risk PRs,
  when authoring was heavily AI-assisted, when primary reviewer confidence is low, when findings conflict,
  or when you need to verify findings with a cross-model or same-model challenger.
  Supports same-model and cross-model configurations for fair comparison.
---

# Challenger Review

An additional independent review pass that strengthens or weakens candidate findings.

## When to use

- Change is medium or high risk (yellow/red lane)
- Authoring was heavily AI-assisted
- Primary reviewer confidence is low
- Findings conflict or remain uncertain
- Configured to run automatically via `enable_challenger_on` setting

## Key requirement

This skill must be usable in two configurations:
- **Same-model challenger:** same model family as primary reviewer, fresh context
- **Cross-model challenger:** different model family from primary reviewer

This allows apples-to-apples comparison between intra-model and cross-model review.

## Inputs

- Evidence pack from [`pr-evidence-builder`](../pr-evidence-builder/SKILL.md)
- Raw diff

Do NOT read primary reviewer conclusions. The challenger always reviews independently.

## Steps

1. **Verify independence before starting.** Confirm you have not read any files from the primary review output directory. Do not access findings from [`fresh-eyes-review`](../fresh-eyes-review/SKILL.md). If any primary review content is in context, stop and restart with a clean context.

2. **Review the evidence pack and raw diff independently.** Approach the code as a separate critic with no knowledge of prior findings.

3. **Produce candidate findings.** Same output format as [`fresh-eyes-review`](../fresh-eyes-review/SKILL.md). Each finding must meet the evidence threshold. If a finding does not meet the threshold, discard it rather than downgrading its severity.

4. **For each finding, indicate whether it:**
   - Confirms a likely issue (new independent evidence for something that may also appear in primary review)
   - Refutes a possible concern (evidence that something is actually safe)
   - Adds a novel finding (something the primary reviewer may have missed)

## Output shape per finding

Same schema as [`fresh-eyes-review`](../fresh-eyes-review/SKILL.md), with `source` set to `"challenger"`. Example:

```json
{
  "source": "challenger",
  "file": "src/auth/token.ts",
  "line": 42,
  "severity": "high",
  "classification": "confirms",
  "title": "JWT secret falls back to hardcoded value",
  "evidence": "process.env.JWT_SECRET ?? 'dev-secret' means any deployment missing the env var silently uses a known secret.",
  "recommendation": "Remove the fallback entirely and throw on missing secret at startup."
}
```

Classification values:
- `"confirms"` — independent evidence supporting an issue that may also appear in the primary review
- `"refutes"` — evidence that a suspected concern is actually safe
- `"novel"` — finding not likely surfaced by the primary reviewer

## Success criteria

- Improves precision or novelty, not just volume
- Reduces shared blind spots between review passes
