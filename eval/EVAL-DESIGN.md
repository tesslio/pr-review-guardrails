# Evaluation Design

## Goal

Measure whether the tile makes human review faster and better — not whether it generates more comments.

## Evaluation modes

Every PR in the corpus is reviewed in all four modes. Results are compared per-PR to control for PR difficulty.

| Mode | Description |
|------|-------------|
| **A: Human-only** | Baseline. Human reviewer with no tile assistance. |
| **B: Same-model independent** | `fresh-eyes-review` only, single model family. |
| **C: Challenger** | `fresh-eyes-review` + `challenger-review` (same-family or cross-family per config). |
| **D: Aggregated + handoff** | Full pipeline: evidence + review + challenger + synthesis + human handoff packet. |

## Corpus design

### Selection criteria

The corpus must include PRs that vary across three axes:

**Risk lane:**
- Green: docs-only, test-only, safe renames, formatting
- Yellow: business logic, moderate refactors, config changes
- Red: auth, migrations, public API, infra, multi-subsystem

**Authorship:**
- Human-authored (no AI co-author trailers)
- Mixed (some commits AI-assisted)
- Heavily AI-authored (majority of commits AI-assisted)

**Size:**
- Small (< 50 lines changed)
- Medium (50-300 lines changed)
- Large (300-1000 lines changed)
- Oversized (> 1000 lines — expected to trigger the split recommendation)

### Minimum corpus size

- 30 PRs per risk lane (90 total minimum)
- At least 10 PRs per authorship category per lane
- At least 5 PRs per size bucket per lane

These are minimums for directional signal. Statistical significance requires larger samples — expand as the tile matures.

### Corpus sources

1. **Historical PRs with known outcomes.** Select merged PRs where post-merge bugs are known. This provides ground truth for escaped defect measurement.
2. **Live PRs with parallel review.** Run the tile alongside human review on incoming PRs. Compare tile findings against actual human review comments.
3. **Seeded PRs with injected defects.** Create PRs with known bugs planted in realistic code. Measures recall directly.

### Corpus metadata per PR

```json
{
  "pr_id": str,
  "repo": str,
  "risk_lane_actual": "green | yellow | red",
  "risk_lane_classified": "green | yellow | red",
  "authorship": "human | mixed | ai_heavy",
  "lines_changed": int,
  "subsystems_touched": int,
  "known_defects": [{
    "file": str,
    "line": int,
    "description": str,
    "severity": "critical | high | medium | low",
    "discovered_via": "post_merge_bug | human_review | seeded"
  }],
  "human_review_comments": int,
  "human_review_findings_valid": int,
  "time_to_merge_hours": float
}
```

## Scorecard

### Per-PR metrics

| Metric | Definition | Why it matters |
|--------|-----------|----------------|
| **Valid finding precision** | valid findings / total findings surfaced | Measures noise. Low precision = developers ignore the tile. |
| **False positives** | findings surfaced that are incorrect or irrelevant | Direct measure of wasted reviewer attention. |
| **Unique valid findings** | valid findings not found by human reviewer | Measures additive value beyond baseline. |
| **Known defect recall** | known defects caught / total known defects | Only measurable on seeded PRs or PRs with post-merge bugs. |
| **Signal-to-noise ratio** | (valid findings) / (valid + false positives + suppressed-but-surfaced) | Composite quality measure. |
| **Comment adoption rate** | findings that led to code changes / findings surfaced | Measures practical usefulness from GitHub comment resolution state. |
| **Reviewer time delta** | time human spent reviewing with tile - time without tile | Negative = tile saved time. Measured via PR timeline. |
| **Time to merge delta** | merge time with tile - merge time without tile | Positive is acceptable if quality improved. Negative is ideal. |
| **Risk classification accuracy** | classified lane matches actual lane | Measures the routing decision. Wrong lane = wrong workflow. |

### Aggregate scorecard

Aggregate per-mode across the corpus, segmented by:

- Risk lane (green / yellow / red)
- Authorship (human / mixed / ai_heavy)
- Challenger config (same-model / cross-model) — mode C and D only

```
┌─────────────────────────┬──────────┬──────────┬──────────┬──────────┐
│ Metric                  │ A: Human │ B: Same  │ C: Chall │ D: Full  │
├─────────────────────────┼──────────┼──────────┼──────────┼──────────┤
│ Valid finding precision  │          │          │          │          │
│ False positives / PR     │          │          │          │          │
│ Unique valid findings/PR │   n/a    │          │          │          │
│ Known defect recall      │          │          │          │          │
│ Signal-to-noise ratio    │          │          │          │          │
│ Comment adoption rate    │          │          │          │          │
│ Reviewer time (median)   │          │          │          │          │
│ Time to merge (median)   │          │          │          │          │
│ Risk classification acc  │   n/a    │          │          │          │
│ Developer trust (1-5)    │          │          │          │          │
└─────────────────────────┴──────────┴──────────┴──────────┴──────────┘
```

### Developer trust measurement

After reviewing a PR with tile assistance, the reviewer answers one question (optional, embedded in PR comment):

> "Did the tile's review packet help you review this PR?" (1 = wasted my time, 3 = neutral, 5 = meaningfully helped)

This is the only subjective metric. Everything else is derived from GitHub data.

## Key comparisons

These are the questions the eval must answer:

1. **Does the tile add value over human-only review?** Compare unique valid findings in modes B/C/D vs mode A.
2. **Does challenger review improve over single-pass?** Compare precision and recall in mode C vs mode B.
3. **Does cross-model challenger beat same-model challenger?** Compare mode C (cross-family) vs mode C (same-family) on the same PRs.
4. **Does the full pipeline justify its cost?** Compare mode D quality gains vs mode D time overhead relative to mode B.
5. **Does the tile perform differently on AI-generated code?** Segment all metrics by authorship category.
6. **Does risk routing work?** Measure classification accuracy and whether red-lane PRs actually had more issues.

## Eval execution

### Phase 1: Historical corpus (no live PRs)

- Select 90+ merged PRs from target repositories
- Run tile in modes B, C, D on each PR offline
- Compare tile findings against actual human review comments and known post-merge bugs
- Score the first scorecard

### Phase 2: Live parallel review

- Run tile alongside human review on incoming PRs
- Collect adoption data from GitHub comment state
- Collect trust scores from optional reviewer feedback
- Update scorecard with live data

### Phase 3: Seeded defect study

- Create PRs with injected defects across risk lanes and authorship types
- Measure recall directly
- Identify blind spots by defect category

## Scorecard output format

```json
{
  "eval_id": str,
  "eval_date": "ISO-8601",
  "corpus_size": int,
  "corpus_breakdown": {
    "by_lane": { "green": int, "yellow": int, "red": int },
    "by_authorship": { "human": int, "mixed": int, "ai_heavy": int }
  },
  "modes": {
    "human_only": { "metrics": {} },
    "same_model": { "metrics": {} },
    "challenger": {
      "same_family": { "metrics": {} },
      "cross_family": { "metrics": {} }
    },
    "aggregated": { "metrics": {} }
  }
}
```

## Success thresholds (v0.1.0)

These are not pass/fail gates — they are directional targets for the first iteration.

| Metric | Target | Rationale |
|--------|--------|-----------|
| Valid finding precision | > 70% | Below this, developers stop reading |
| False positives per PR | < 2 | Each false positive costs trust |
| Unique valid findings per PR | > 0.5 | The tile must find things humans miss |
| Comment adoption rate | > 25% | The research brief reports AI adoption rates of 1-19%; beating the high end is the bar |
| Risk classification accuracy | > 85% | Wrong lane = wrong workflow |
| Developer trust (median) | >= 3 | Neutral or better; below 3 means the tile is in the way |
