# Setting Up a PR Review Automation Pipeline

## Problem/Feature Description

Your team has grown to 12 engineers and the volume of pull requests has made manual first-pass triage unsustainable. You've been asked to write a shell script that automates the initial evidence-gathering phase whenever a new PR is opened. The script needs to collect all the raw material a human (or downstream tool) will need to reason about the change: what changed, which subsystems are affected, whether tests pass, whether any security or quality issues exist, and whether the PR is even a reasonable size to review.

The engineering lead has one hard requirement: the pipeline must be resilient when GitHub's API is having problems, and it should not block the team while verifiers are running. The output must be a single well-structured JSON file that a downstream review agent can consume without needing to re-run anything.

## Output Specification

Produce the following files:

1. `run_pr_review_pipeline.sh` — a shell script that orchestrates the full evidence-gathering pipeline for a given PR. The script should accept `--pr <number>` and `--repo <owner/repo>` arguments and produce a final `evidence-pack.json` in the working directory.

2. `pipeline_design.md` — a brief design document (300–500 words) explaining:
   - The sequence and parallelism of steps in the pipeline
   - How the script handles GitHub API unavailability
   - How oversized PRs are detected and handled
   - What the evidence pack JSON structure contains at a high level
   - How risk classification handles uncertainty

The design document should be detailed enough that another engineer could implement an equivalent pipeline independently.
