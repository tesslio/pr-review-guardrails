# Finding Synthesizer — Reference Implementation

Reference Python implementation for the deduplication and ranking logic. The `dedupe_findings.py` script in `scripts/` implements this fully; this document explains the algorithm for manual application or adaptation.

## Deduplication algorithm

### Step 1: Group findings into clusters

For each pair of findings, check if they should be merged:

```python
def should_merge(a, b):
    # Must be in the same file
    if a["file"] != b["file"]:
        return False

    # Check line overlap (within 3-line tolerance)
    if lines_overlap(a["line_start"], a["line_end"],
                     b["line_start"], b["line_end"], tolerance=3):
        # Overlapping lines — check description similarity
        if text_similarity(a["title"], b["title"]) > 0.7:
            return True  # Exact match
        if text_similarity(a["why_it_matters"], b["why_it_matters"]) > 0.6:
            return True  # Semantic overlap

    # No line overlap — check for very similar descriptions
    if text_similarity(a["title"], b["title"]) > 0.8:
        return True  # Same issue, different line attribution

    return False
```

### Step 2: Merge each cluster

For each cluster of related findings:

1. **Pick the canonical finding** — the one with the highest `severity × confidence`
2. **Check for conflicts** — if findings in the cluster recommend different actions (e.g., one says "fix", another says "discuss"), mark as contested
3. **Record corroboration** — list all non-canonical sources as `corroborated_by`
4. **Boost confidence** — if multiple independent sources (different `source` values) agree:
   - low → medium
   - medium → high
   - high → high (no change)

```python
def merge_cluster(findings):
    canonical = max(findings, key=lambda f: (
        SEVERITY_ORDER[f["severity"]],
        CONFIDENCE_ORDER[f["confidence"]],
    ))

    sources = [f["source"] for f in findings]
    actions = set(f["action"] for f in findings)

    merged = canonical.copy()
    merged["corroborated_by"] = [
        f["source"] for f in findings if f is not canonical
    ]

    if len(actions) > 1 and {"fix", "discuss"}.issubset(actions):
        merged["contested_by"] = [
            f["source"] for f in findings
            if f["action"] != canonical["action"]
        ]
    else:
        merged["contested_by"] = []

    # Boost confidence if independently corroborated
    if len(set(sources)) > 1:
        merged["merged_confidence"] = boost(canonical["confidence"])
    else:
        merged["merged_confidence"] = canonical["confidence"]

    return merged
```

## Ranking formula

After deduplication, rank survivors by:

```
score = SEVERITY_WEIGHT[severity] × CONFIDENCE_WEIGHT[confidence] × VERIFICATION_WEIGHT[verification_support]
```

Where:

| Level | Severity weight | Confidence weight | Verification weight |
|-------|----------------|-------------------|-------------------|
| critical / high | 3 | 3 | 3 (verifier-backed) |
| high / medium | 2 | 2 | 2 (hunk-level code) |
| medium / low | 1 | 1 | 1 (contextual reasoning) |

Example:
| Finding | Severity | Confidence | Verification | Score |
|---------|----------|-----------|--------------|-------|
| SQL injection in login handler | 3 (critical) | 3 (high) | 3 (semgrep hit) | 27 |
| Null deref in permission guard | 2 (high) | 3 (high) | 2 (hunk-level) | 12 |
| Possible race in cache update | 2 (high) | 1 (low) | 1 (contextual) | 2 |

The third finding (score 2) would likely be suppressed by the evidence threshold since its only evidence is contextual reasoning at low confidence.

## Suppression rules

After ranking, suppress findings that:

1. **Are style-only and already covered by a linter** — check if the verifier results include a linter pass for the same file. If the linter ran and passed, style findings from reviewers are noise.

2. **Have low confidence with only contextual reasoning** — if `evidence.type == "contextual_reasoning"` and `confidence == "low"`, suppress. The evidence threshold rule requires at least one concrete evidence source.

3. **Duplicate verifier output** — if a reviewer finding restates exactly what a verifier already reported (same file, same line, same issue), suppress the reviewer's copy and keep the verifier finding (which has deterministic evidence).

Suppressed findings are retained with `suppressed: true` and `suppression_reason` set. They appear in eval data but not in the reviewer packet.

## Conflict handling

When two reviewers disagree on the same code:

- Both positions are surfaced in the reviewer packet
- The finding is marked `contested_by: [disagreeing source]`
- The action is set to `"discuss"` regardless of individual recommendations
- `requires_human` is set to `true`

This ensures contested findings always reach a human reviewer for adjudication.
