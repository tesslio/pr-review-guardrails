---
name: finding-synthesizer
description: |
  Turn many candidate findings from reviewers and verifiers into a small,
  decision-useful set. Deduplicates, ranks, and suppresses weak findings to
  consolidate review results into a prioritized, actionable list with severity
  ratings and merged confidence scores. Use when you need to merge findings,
  consolidate feedback, prioritize issues, or summarize review output after
  review passes are complete and before human handoff. Trigger phrases:
  "consolidate review results", "merge findings", "deduplicate feedback",
  "prioritize issues from review", "summarize reviewer output".
  The evidence threshold is the filter — not an arbitrary cap.
---

# Finding Synthesizer

Merge, deduplicate, and rank all candidate findings into a compact set worth a human's attention.

## When to use

- After [`fresh-eyes-review`] and optionally [`challenger-review`] have produced candidate findings
- Before [`human-review-handoff`]
- **Skip this step entirely if there is only one review source with fewer than 5 findings** — pass findings directly to handoff. Synthesis adds value when merging multiple sources or pruning a large finding set, not when reformatting a short list.

## Inputs

- Candidate findings from `fresh-eyes-review`
- Candidate findings from `challenger-review` (if it ran)
- Verifier findings from the evidence pack

### Example input finding (JSON)

Each source produces findings in this shape:

```json
{
  "source": "fresh-eyes-review",
  "file": "auth/login.py",
  "line_start": 42,
  "line_end": 55,
  "issue": "SQL injection via unsanitized user input in query construction",
  "severity": 3,
  "confidence": 3,
  "evidence": "User-supplied `username` concatenated directly into SQL string at line 47.",
  "verification_support": 3
}
```

Multiple such objects (one per finding, across all sources) form the input list to the synthesis steps below.

## Steps

1. **Merge all finding sources.** Collect findings from all reviewers and verifiers into one list.

2. **Deduplicate** — apply the following strategies in order:
   - Exact match (same file, same line range, same issue): merge, keep strongest evidence
   - Semantic overlap (different wording, same underlying issue): merge, cite both sources
   - Corroboration (multiple sources flag the same area): boost confidence, note agreement
   - Conflict (two reviewers disagree): surface both positions, mark as contested for human judgment

   Apply these strategies directly. If the tile's `dedupe_findings.py` script is available, you may use it — but do not fail or stop if it is missing. See `REFERENCE.md` for detailed algorithm documentation.

3. **Suppress weak findings:**
   - Discard style-only findings already covered by linters
   - Discard weak speculation that doesn't meet the evidence threshold
   - Retain suppressed findings in the data for eval, but do not surface them

4. **Rank survivors** by `severity × confidence × verification_support`.

   Example ranking with sample values:
   | Finding | Severity (1–3) | Confidence (1–3) | Verification Support (1–3) | Score |
   |---------|---------------|-----------------|--------------------------|-------|
   | SQL injection in login handler | 3 | 3 | 3 | 27 |
   | Unhandled null in parser | 2 | 3 | 2 | 12 |

   Higher scores surface first; findings below the evidence-threshold score are suppressed.

5. **Surface all findings that clear the evidence threshold.** No arbitrary caps.

6. **Handle missing sources.** If a reviewer source returned malformed or empty output, skip that source, proceed with remaining sources, and note the missing source in the output metadata.

## Output per finding (after synthesis)

Each finding gains:
- `corroborated_by`: list of agreeing sources
- `contested_by`: list of disagreeing sources
- `merged_confidence`: high | medium | low
- `suppressed`: true/false
- `suppression_reason`: why it was suppressed (null if not suppressed)

## Success criteria

- Signal-to-noise ratio is visibly better than raw reviewer output
- Zero findings surfaced without evidence
