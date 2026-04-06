# tessl-labs/pr-review-guardrails

Evidence-first pull request review. Builds a dossier, classifies risk, hands a structured brief to a human who makes the call.

## Why

AI code review comments get adopted 1-19% of the time. Human reviewer comments land at significantly higher rates. The gap is signal-to-noise: AI reviewers flood PRs with findings that are either obvious or wrong. Developers learn to ignore the firehose.

This plugin doesn't try to be a better bug finder. It builds an evidence pack about the PR, classifies the risk into lanes, and produces a structured brief so the human reviewer can focus on the questions only a human can answer.

The design is grounded in the [Cross-model AI PR Review Research Brief](https://github.com/tesslio/pr-review-guardrails/blob/main/docs/Cross-model%20AI%20PR%20Review%20Brief.md) and the [PR Review Guardrails Spec](https://github.com/tesslio/pr-review-guardrails/blob/main/docs/PR%20Review%20Guardrails%20Spec.md).

## The pipeline

![Pipeline: PR Diff flows through Evidence Builder (risk classification), Fresh-Eyes Reviewer, optional Challenger, Synthesizer, Human Handoff, and Retrospective](https://raw.githubusercontent.com/tesslio/pr-review-guardrails/main/pipeline.svg)

Six skills, executed in sequence:

1. **Evidence Builder** — reads the diff, maps changed files, runs deterministic verifiers (linters, type checkers, secret scanners), and classifies risk into lanes: green (routine), yellow (needs attention), red (security-relevant, requires deep review). Everything downstream flows from this classification.

2. **Fresh-Eyes Reviewer** — gets the evidence pack and the raw diff. Hunts for problems, but only problems the evidence supports. No hallucinating security vulnerabilities in a docs-only PR. Produces candidate findings, not verdicts.

3. **Challenger** *(optional)* — a second independent review pass. Cross-model or same-model, configurable. Strengthens or weakens candidate findings. Research says independent review works as a verification layer.

4. **Finding Synthesizer** — deduplicates, ranks, and compresses all findings into a single brief with evidence, confidence levels, and a recommendation for what to focus on.

5. **Human Handoff** — formats the brief for the person who actually decides whether to merge. Risk classification up front, findings with evidence, and explicit gaps where the plugin didn't have coverage.

6. **Retrospective** *(optional)* — runs after the human makes their call. Compares the plugin's findings against the human's decision. The feedback loop.

## What you get

A brief, not a wall of findings. It starts with risk classification — green, yellow, or red — so you know immediately how much attention the PR needs. Each finding comes with evidence: specific lines, why it was flagged, and a confidence level. The brief also tells you what it *didn't* check.

## Install

```
tessl install tessl-labs/pr-review-guardrails
```

Point it at a PR you've already reviewed — compare its brief against what you found.

## Eval corpus

43 scenarios across four test repositories (`payments-api`, `web-dashboard`, `data-service`, `deploy-infra`), covering:

- Docs-only and test-only PRs (should produce zero findings)
- Hardcoded secrets, timing attacks, TOCTOU races, double refunds
- CSV injection, IDOR, stale auth caches, log injection
- Infrastructure: unencrypted SNS, open security groups, Glacier lifecycle traps, same-AZ replicas
- Oversized PRs, missing descriptions, compilation failures

Plugin scores 97.7% against a 66.6% baseline (Claude Opus with no guidance). The gap comes from false positive suppression and risk classification, not raw bug detection.

## Steering rules

| Rule | Purpose |
|------|---------|
| `review-boundaries` | What the plugin reviews and what it leaves to humans |
| `reviewer-independence` | Reviewer context must be isolated from authoring context |
| `evidence-threshold` | Findings must be grounded, scoped, and non-duplicative |
| `comment-quality` | Precision over volume — fewer, sharper findings |
| `risk-routing` | Green/yellow/red lane classification criteria |
| `human-escalation` | When and how to escalate to human review |

## Project structure

```
tile.json                    # Tile manifest
skills/
  pr-evidence-builder/       # Risk classification and evidence pack
  fresh-eyes-review/         # Independent critique
  challenger-review/         # Optional second review pass
  finding-synthesizer/       # Dedupe, rank, compress
  human-review-handoff/      # Format brief for human
  review-retrospective/      # Post-decision feedback loop
rules/                       # Steering rules
scripts/                     # Supporting automation
evals/                       # 43 eval scenarios with criteria
```

## License

See [tile.json](tile.json) for tile metadata.
