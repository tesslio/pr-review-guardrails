# Tile Spec: `tessl-labs/pr-review-guardrails`

## Summary
A Tessl tile for improving pull request review quality by combining deterministic evidence collection, independent AI review, optional challenger review, aggressive finding suppression, and explicit human handoff.

## Primary research document
- [Research brief](sandbox:/mnt/data/AI%20PR%20Review%20Research%20Brief.md)

This is the single authoritative research document for this tile spec. It consolidates the original brief and the later revisions on cross-model vs intra-model review, evaluation design, and workflow implications.

## Research grounding
This tile is grounded in the research brief on AI-powered pull request review and in the studies and product patterns summarized there.

### 1. The tile is designed against review theater
The brief argues that the central risk is not simply AI reviewing AI-generated code, but drift into a pattern where AI generates code, AI generates review comments, and humans skim both without adding real scrutiny. That is the core reason this tile is designed as an evidence-first, human-supervised review layer rather than an autonomous reviewer.

Relevant research and evidence referenced in the brief:
- Google Research, *Modern Code Review: A Case Study at Google*
- *Understanding Reviewer Pain Points and the Potential for LLMs in Code Review*
- *Understanding How Software Engineers Interact with AI-Assisted Code Reviews*
- *Human-AI Synergy in Agentic Code Review*

### 2. The tile prioritizes signal-to-noise over comment volume
The brief concludes that AI review often creates activity without proportional value, and that usefulness depends heavily on whether comments are grounded, specific, and worth the cognitive effort to verify. That is why this tile aggressively suppresses weak findings and uses synthesis as a first-class step. The evidence threshold controls volume, not an arbitrary cap.

Relevant research and evidence referenced in the brief:
- *Are AI Reviews Better than Human Reviews? A Case Study of AI Code Review GitHub Actions*
- *How Does Automated Code Review Work in Practice? A Case Study of Automated Reviews in Pull Requests*
- *CR-Bench*

### 3. The tile moves AI earlier in the workflow
The brief recommends moving AI earlier into author-side and pre-PR workflows, where it can remove low-value issues before the PR becomes a burden on human reviewers. That is why the tile begins with `pr-evidence-builder` and supports a preflight mode before comments are generated.

Relevant research and evidence referenced in the brief:
- *Understanding Reviewer Pain Points and the Potential for LLMs in Code Review*
- product patterns from CodeRabbit, GitHub Copilot, and other review tools discussed in the brief

### 4. The tile treats independent review as more important than model branding
The brief does not support a simplistic claim that a different model family will reliably review code better than the model that wrote it. The stronger conclusion is narrower: independent review is preferable to same-context self-review, and cross-model review is promising as a challenge layer rather than a substitute for human review. That is why the tile is built around reviewer roles and separation of contexts, not around hardcoded model names.

Relevant research and evidence referenced in the brief:
- *Using LLMs to Review AI-Generated Code*
- *SWR-Bench: Evaluating Code Review in Context*
- *Self-Preference Bias in LLM-as-a-Judge*
- multi-agent and verification patterns summarized in the brief

### 5. The tile includes both intra-model and cross-model paths
Because the brief argues that cross-model review must be compared fairly against same-model independent review, the tile includes both `fresh-eyes-review` and `challenger-review`. This allows Tessl to compare same-model, cross-model, and aggregated review modes on the same PR corpus instead of assuming cross-model diversity is always the winning strategy.

Relevant research and evidence referenced in the brief:
- *SWR-Bench: Evaluating Code Review in Context*
- the cross-model and intra-model analysis in the revised research brief

### 6. The tile makes verification first-class
The brief repeatedly shows that trust improves when findings are tied to concrete evidence, repository context, and deterministic checks. Product documentation in the brief also shows that leading tools increasingly emphasize verification, repository context, and ranked findings rather than unfiltered comment generation. That is why this tile centers deterministic verifiers, evidence packs, hotspot mapping, and finding synthesis.

Relevant research and evidence referenced in the brief:
- *CR-Bench*
- *SWR-Bench: Evaluating Code Review in Context*
- GitHub Copilot code review docs
- GitLab Duo Code Review docs
- Claude Code Review docs
- Greptile, Qodo Merge, and CodeRabbit product patterns summarized in the brief

### 7. The tile keeps humans responsible for high-risk review domains
The brief is explicit that humans still own intent, architecture, public API changes, migrations, rollout-sensitive logic, trade-offs, and final accountability. That is why the tile includes hard routing and escalation rules, and why red-lane changes always end in explicit human handoff rather than automated verdicts.

Relevant research and evidence referenced in the brief:
- *Human-AI Synergy in Agentic Code Review*
- the workflow recommendations and division-of-labor section in the revised research brief

### 8. The tile is built to be evaluated, not just deployed
The brief argues that review quality should be measured using false-positive rate, signal-to-noise ratio, comment adoption, reviewer time, time to merge, escaped defects, and developer trust, while also distinguishing between human-authored and AI-generated PRs and between pre-PR and PR-stage review. That is why this tile includes `review-retrospective`, provenance capture, and an explicit evaluation plan in the spec.

Relevant research and evidence referenced in the brief:
- *Are AI Reviews Better than Human Reviews? A Case Study of AI Code Review GitHub Actions*
- *How Does Automated Code Review Work in Practice? A Case Study of Automated Reviews in Pull Requests*
- *CR-Bench*
- the evaluation framework in the revised research brief

## Product goal
Create a reusable PR-review tile that helps teams:

- catch local and checkable defects earlier
- reduce false positives and repetitive review comments
- distinguish low-risk changes from human-review-only changes
- compare intra-model and cross-model review modes fairly
- generate a compact reviewer packet that makes human review faster and better

---

## Non-goals
The tile will not:

- approve or block PRs autonomously
- replace required human review for high-risk changes
- act as an architecture reviewer of record
- assume cross-model review is always better than same-model independent review
- optimize for maximum comment count

---

## Tile contents

### Rules
- review-boundaries
- risk-routing
- evidence-threshold
- comment-quality
- human-escalation
- reviewer-independence

### Skills
- `pr-evidence-builder`
- `fresh-eyes-review`
- `challenger-review`
- `finding-synthesizer`
- `human-review-handoff`
- `review-retrospective`

### Supporting scripts
- `collect_pr_context.py`
- `classify_change_risk.py`
- `run_verifiers.sh`
- `map_diff_hotspots.py`
- `check_required_artifacts.py`
- `dedupe_findings.py`
- `build_reviewer_packet.py`
- `record_review_outcomes.py`
- `detect_ai_authorship.py`

### Documentation
- review rubric
- risk taxonomy
- reviewer packet format
- examples of strong vs weak findings
- evaluation guidance

---

## Reviewer modes
The tile should support multiple review modes behind the same interface.

### Mode A: author-side preflight only
Use when:
- change is low risk
- user wants early feedback before opening PR
- repository or branch is still in active authoring mode

Behavior:
- collect context
- run deterministic verifiers
- summarize likely hotspots
- produce preflight guidance
- no PR comments generated

### Mode B: independent same-model review
Use when:
- one model is available
- change is low or medium risk
- user wants a fresh-eyes critique without extra model cost

Behavior:
- isolate reviewer context from authoring context
- review the evidence pack and diff as a separate critic
- emit candidate findings only

### Mode C: challenger review
Use when:
- change is medium or high risk
- authoring was heavily AI-assisted
- primary reviewer confidence is low
- findings conflict or remain uncertain

Behavior:
- run a second independent review pass
- challenger may be same-family or cross-family depending on configuration
- challenger does not approve or block
- challenger strengthens or weakens candidate findings

### Mode D: aggregated review with human handoff
Use when:
- change is high risk
- multiple independent review sources are available
- a human reviewer needs a concise decision packet

Behavior:
- merge deterministic findings + reviewer findings
- dedupe and rank
- mark unresolved assumptions
- produce human-review packet

---

## Why cross-model review is optional, not foundational
The tile should not be defined as “use a different model to review code written by another model.”

Instead, it should be defined as “create an independent review layer.”

Cross-model review is one implementation of reviewer independence. Intra-model fresh-eyes review is another. The tile should support both and evaluate them empirically.

That means:
- same-model independent review is the baseline
- cross-model review is a challenger strategy
- synthesis and verification matter more than raw reviewer diversity

---

## Repository configuration: `.pr-review/`

The tile reads optional per-repo configuration from a `.pr-review/` directory at the repository root. All files are optional — the tile has sensible defaults without any of them.

| File | Used by | Purpose |
|------|---------|---------|
| `subsystems.json` | `collect_pr_context.py` | Explicit subsystem map when CODEOWNERS and directory structure are insufficient. Format: `{ "api": ["src/api/**"], "worker": ["src/worker/**", "src/jobs/**"] }` |
| `verifiers.json` | `run_verifiers.sh` | Repo-specific verification commands beyond auto-discovered tools. Format: `[{ "name": str, "command": str, "timeout_ms": int }]` |
| `required-artifacts.json` | `check_required_artifacts.py` | Override default artifact requirements per risk lane. Allows repos to add or relax requirements beyond the tile defaults. |
| `risk-overrides.json` | `classify_change_risk.py` | Repo-specific path patterns that force a risk lane (e.g., always treat `billing/` as red). Format: `[{ "pattern": str, "lane": "yellow" \| "red" }]` — can escalate only, never downgrade. |

Discovery: scripts check for the `.pr-review/` directory once during `pr-evidence-builder` and pass relevant config to downstream scripts. If the directory does not exist, all scripts use defaults.

---

## End-to-end workflow

### Stage 1: Context and evidence build
The tile gathers:
- PR title and description
- linked issue, task, or ticket
- changed files
- changed subsystems
- related tests
- ownership signals if available
- migration/config/security-sensitive touches
- recent context around touched files if available

Then it runs deterministic checks:
- tests
- typecheck
- lint
- static analysis
- secret scanning
- dependency/security checks
- any repo-specific verifiers

Output:
- machine-readable evidence pack
- concise summary for later reviewers

### Stage 2: Risk classification
The tile assigns a risk lane.

#### Green
Examples:
- docs-only
- test-only
- safe renames
- formatting or mechanical cleanup
- simple internal refactors with strong test coverage

#### Yellow
Examples:
- business logic changes
- moderate refactors
- non-public API changes
- config changes with bounded blast radius

#### Red
Examples:
- auth/permissions
- payments/billing
- migrations
- public API changes
- rollout-sensitive logic
- multi-subsystem changes
- infra and deployment logic
- concurrency or caching changes
- secrets or trust boundaries

Risk lane determines which skills run and how findings are surfaced.

### Stage 3: Independent review
For green and yellow lanes, run `fresh-eyes-review`.

For yellow and red lanes, optionally or automatically run `challenger-review` based on config.

Each reviewer produces:
- candidate findings
- confidence assessment
- why the finding matters
- evidence source
- whether the issue appears local/checkable or requires human judgment

### Stage 4: Synthesis
The synthesizer:
- merges tool and reviewer findings
- deduplicates overlap
- suppresses style-only findings already covered by linters
- suppresses weak speculation that doesn't meet the evidence threshold
- ranks findings by severity and evidence quality
- surfaces all findings that clear the threshold — no arbitrary caps

### Stage 5: Human handoff
The handoff skill produces:
- what changed
- why it changed
- risk lane
- what was verified
- top findings
- unresolved assumptions
- explicit human-review-only questions

---

## Skill specs

## 1. `pr-evidence-builder`
### Purpose
Build a compact, trustworthy evidence pack before deeper review starts.

### Inputs
- PR diff or branch diff
- PR title/description
- linked issue/task if available
- repository instructions if available

### Outputs
- diff summary
- touched subsystems
- detected risk factors
- verifier results
- hotspot map
- missing artifacts list

### Oversized diff handling
If the diff exceeds the model's usable context window, the skill must:
- detect this early, before hotspot mapping or risk classification
- surface a clear blocker: "this PR is too large for effective AI review — consider splitting"
- still allow verifiers to run (they are independent of context limits)
- skip the AI review pipeline entirely rather than review partial code

### Success criteria
- reviewers receive enough context to avoid shallow generic feedback
- missing artifacts are surfaced before human review starts
- oversized diffs are caught early with an actionable split recommendation

---

## 2. `fresh-eyes-review`
### Purpose
Provide an independent critique using a clean reviewer context.

### Rules
- must not run in the same context as code generation
- must behave as critic, not co-author
- must produce candidate findings, not verdicts

### Output shape per finding
- title
- impacted file/hunk
- why it matters
- evidence
- confidence
- lane recommendation: local-fix / verify / human-judge

### Success criteria
- fewer but sharper findings than generic review bots
- minimal repetition
- hunk-level feedback where possible

---

## 3. `challenger-review`
### Purpose
Stress-test the primary review with an additional independent reviewer.

### Key requirement
This skill must be usable in two configurations:
- same-model challenger
- cross-model challenger

That allows apples-to-apples comparison between intra-model and cross-model review.

### Behavior
- review only the evidence pack and code context needed for review
- do not read primary reviewer conclusions — the challenger always reviews independently
- either confirm, refute, or add candidate findings

### Success criteria
- improves precision or novelty, not just volume
- reduces shared blind spots

---

## 4. `finding-synthesizer`
### Purpose
Turn many candidate findings into a small decision-useful set.

### Hard responsibilities
- dedupe overlapping findings
- discard low-evidence style noise
- merge corroborating evidence
- prioritize by severity × confidence × verification support
- surface ALL findings that clear the evidence threshold — no arbitrary caps
- if a reviewer source returns malformed or empty output: skip that source, proceed with remaining sources, and note the missing source in the reviewer packet metadata

### Success criteria
- signal-to-noise ratio is visibly better than raw reviewer output
- zero findings surfaced without evidence (the threshold is the filter, not a number)

---

## 5. `human-review-handoff`
### Purpose
Produce a reviewer packet designed for a human reviewer, not a machine.

### Packet sections
- change summary
- linked intent
- risk lane
- verification status
- top findings
- unresolved assumptions
- questions requiring human judgment
- recommended review focus areas

### Success criteria
- human reviewer can understand where to spend attention quickly
- packet makes human review faster without pretending to replace it

---

## 6. `review-retrospective`
### Purpose
Learn which review patterns actually helped after merge or review completion.

### Data source: GitHub (passive capture, no developer forms)
All outcome data is collected from GitHub API events. No manual input required.

#### From PR review comments (`gh api repos/{owner}/{repo}/pulls/{pr}/comments`)
- finding marked "resolved" → accepted
- finding left unresolved at merge → ignored
- suggested change committed → accepted with exact fix
- reply disagreeing with finding → rejected (capture reply text for eval)

#### From PR timeline (`gh api repos/{owner}/{repo}/pulls/{pr}/timeline`)
- time from tile comment to merge → review overhead signal
- number of review rounds after tile comments → iteration cost
- whether PR was closed without merge → possible tile-induced abandonment (flag for review)

#### From post-merge issues (`gh api search/issues?q=repo:{owner}/{repo}+linked:{pr}`)
- issues opened referencing the merged PR → candidate escaped defects
- bug labels on those issues → confirmed escaped defects

#### From commit metadata (`git log --format='%(trailers)'`)
- `Co-Authored-By` trailers → AI authorship tagging (see AI authorship detection below)
- reviewer mode used → same-model vs challenger correlation with outcomes

### Captured outcomes
- finding accepted / rejected / ignored / superseded (from GitHub comment state)
- whether the human fixed the exact issue or an alternative issue (from committed suggestions vs manual commits)
- merge time delta (from PR timeline)
- escaped defects (from post-merge linked issues)
- AI authorship correlation (from commit trailers)

### Success criteria
- tile can be evaluated on usefulness, not just output volume
- all data captured passively — zero developer friction

---

## Evidence pack schema

The evidence pack is the composed artifact produced by `pr-evidence-builder` from individual script outputs. It is the single input to `fresh-eyes-review`, `challenger-review`, and `finding-synthesizer`. Reviewer skills receive ONLY this pack and the raw diff — never authoring context.

```json
{
  "schema_version": "1.0",
  "generated_at": "ISO-8601 timestamp",
  "wall_clock_ms": int,

  "pr": {
    "number": int,
    "title": str,
    "description": str,
    "labels": [str],
    "url": str
  },

  "authorship": {
    "ai_assisted": bool,
    "ai_tools": [str],
    "ai_commit_ratio": float,
    "total_commits": int
  },

  "diff": {
    "stats": {
      "files_changed": int,
      "insertions": int,
      "deletions": int
    },
    "touched_files": [{
      "path": str,
      "change_type": "added" | "modified" | "deleted" | "renamed",
      "subsystem": str,
      "insertions": int,
      "deletions": int
    }],
    "subsystems": [str],
    "raw_diff": str
  },

  "context": {
    "linked_issues": [{
      "number": int,
      "title": str,
      "body": str,
      "labels": [str]
    }],
    "related_tests": [{
      "source_file": str,
      "test_file": str,
      "test_exists": bool
    }],
    "owners": [{
      "path_pattern": str,
      "owners": [str]
    }],
    "repo_instructions": str | null
  },

  "risk": {
    "lane": "green" | "yellow" | "red",
    "confidence": "high" | "medium" | "low",
    "factors": [{
      "factor": str,
      "files": [str],
      "severity": "moderate" | "red"
    }],
    "override_applied": bool,
    "override_source": str | null
  },

  "verification": {
    "verifiers": [{
      "name": str,
      "status": "pass" | "fail" | "warn" | "skipped" | "timeout",
      "findings": [{
        "file": str,
        "line": int | null,
        "message": str,
        "severity": "error" | "warning" | "info"
      }],
      "duration_ms": int
    }],
    "summary": {
      "passed": int,
      "failed": int,
      "warnings": int,
      "skipped": int
    }
  },

  "hotspots": [{
    "file": str,
    "line_start": int,
    "line_end": int,
    "category": str,
    "why": str,
    "risk_contributing": bool
  }],

  "missing_artifacts": [{
    "artifact": str,
    "why_required": str,
    "suggested_location": str,
    "required": bool
  }]
}
```

### Design notes
- `raw_diff` is included so reviewer skills can inspect actual code, not just metadata. If the diff exceeds the model's usable context window, the tile should not truncate — it should block AI review and recommend splitting the PR (see `pr-evidence-builder` oversized diff handling).
- `repo_instructions` captures contributing guides, PR templates, or `.pr-review/` config that the reviewer should respect.
- The pack is self-contained. A reviewer skill should be able to produce findings from this artifact alone without making additional API calls or reading additional files.
- `schema_version` is included for forward compatibility. Backward compatibility and migration rules are a post-v1.0 concern — the schema will change significantly before stabilizing.

---

## Candidate finding schema

This is the output format for `fresh-eyes-review` and `challenger-review`. The `finding-synthesizer` consumes arrays of these from all review sources, dedupes and ranks them, and passes the survivors to `human-review-handoff`.

```json
{
  "finding_id": str,          // UUID — dedup works on content (file/line/semantics), not IDs
  "source": "fresh_eyes" | "challenger" | "verifier",
  "title": str,
  "file": str,
  "line_start": int | null,
  "line_end": int | null,
  "hunk": str | null,
  "why_it_matters": str,
  "evidence": {
    "type": "verifier_output" | "hunk_level_code" | "repo_policy" | "contextual_reasoning",
    "detail": str
  },
  "confidence": "high" | "medium" | "low",
  "severity": "critical" | "high" | "medium" | "low",
  "action": "fix" | "verify" | "discuss",
  "requires_human": bool
}
```

### After synthesis, each finding gains:
```json
{
  "corroborated_by": [str],
  "contested_by": [str],
  "merged_confidence": "high" | "medium" | "low",
  "suppressed": bool,
  "suppression_reason": str | null
}
```

Suppressed findings are retained in the data for eval but not surfaced in the reviewer packet.

---

## Supporting script contracts

## `collect_pr_context.py`
Collects structured PR context and writes a normalized JSON artifact. Runs in parallel with `run_verifiers.sh`.

### Inputs
- PR number or branch diff (via `gh api` or `git diff`)
- repo root path

### Responsibilities
- parse diff metadata (files changed, insertions, deletions, renames)
- enumerate touched files with change type (added, modified, deleted, renamed)
- infer subsystem clusters using the following fallback chain:
  1. CODEOWNERS if present
  2. repo-specific subsystem map from `.pr-review/subsystems.json` if present
  3. top-level directory as subsystem (e.g. `src/api/` → "api", `src/worker/` → "worker")
  4. if the repo is flat or has no meaningful directory structure, treat everything as one subsystem (multi-subsystem detection will not trigger — conservative but honest)
- attach linked issue/task text if available (from PR description links or GitHub issue references)
- locate nearby tests: for each changed source file, find corresponding test files by convention (e.g., `foo.py` → `test_foo.py`, `foo.ts` → `foo.test.ts`)
- extract likely owners from CODEOWNERS or git blame frequency on touched files
- detect AI authorship via `detect_ai_authorship.py`
- capture PR description, title, and labels

### Failure handling
- GitHub API unreachable: retry with backoff (3 attempts, 2s/4s/8s). If still unavailable, produce a partial evidence pack from local git data only (diff, file list, commit trailers). Mark `context.linked_issues`, `context.owners`, and PR metadata as unavailable. The review pipeline can still run on local data — findings will be less contextual but not absent.
- Missing CODEOWNERS and no `.pr-review/subsystems.json`: fall through the subsystem inference chain (see above). This is expected, not an error.

### Output schema
```json
{
  "pr": { "number": int, "title": str, "description": str, "labels": [str] },
  "diff_stats": { "files_changed": int, "insertions": int, "deletions": int },
  "touched_files": [{ "path": str, "change_type": str, "subsystem": str }],
  "subsystems": [str],
  "linked_issues": [{ "number": int, "title": str, "body": str }],
  "related_tests": [{ "source": str, "test": str, "exists": bool }],
  "owners": [{ "path_pattern": str, "owners": [str] }],
  "ai_authorship": { "ai_assisted": bool, "ai_tools": [str], "ai_commit_ratio": float }
}
```

---

## `classify_change_risk.py`
Assigns risk lane and contributing factors. This is the routing decision that determines which skills run — if it gets a classification wrong, the whole workflow degrades silently. Treat this as the most important script in the tile.

### Inputs
- touched file paths
- diff stats (additions, deletions, files changed)
- subsystem map from `collect_pr_context.py`
- repo-specific risk config if available (path patterns, ownership rules)

### Risk factors (each contributes to lane escalation)
- auth-sensitive files touched (auth/, permissions/, ACL, trust boundary)
- migration files touched (db/migrate, alembic, flyway, schema changes)
- public API surface changed (OpenAPI spec, proto files, exported types, REST routes)
- config/deploy/infra changed (Terraform, Helm, CI/CD, Dockerfile, env config)
- multiple subsystems changed in one PR
- low test coverage around touched area (if coverage data available)
- concurrency primitives touched (locks, mutexes, channels, async boundaries)
- cache invalidation logic changed
- secrets, keys, or trust-boundary code touched
- rollout/feature-flag logic changed

### Classification rules
- **Green:** all factors absent, OR only docs/tests/formatting/safe-renames touched
- **Yellow:** one or two moderate factors present, no red factors
- **Red:** any red factor present (auth, migration, public API, infra, secrets, multi-subsystem)
- **When confidence is low:** round UP. If the classifier cannot determine the lane with high confidence, classify as the next higher lane. A false red costs one extra review pass. A false green can miss a real issue.

### Override mechanism
- PR description can include explicit risk override (`risk: red`) for cases where the author knows something the classifier doesn't
- Override can escalate only, never downgrade (author can say "this is riskier than it looks" but not "trust me it's fine")

### Outputs
- risk lane: green | yellow | red
- contributing factors with file-level attribution
- classification confidence: high | medium | low
- whether override was applied

---

## `run_verifiers.sh`
Runs deterministic checks and captures normalized outputs. Runs in parallel with `collect_pr_context.py`.

### Responsibilities
- discover and invoke repo-native verification commands
- run all verifiers in parallel where possible
- normalize success/failure/skipped outputs into a common format
- enforce a per-verifier timeout (default 60s) so a hung linter doesn't block the pipeline
- on timeout: record the verifier as `timeout` in the output — do not retry, do not block the pipeline
- write machine-readable verifier summary

### Verifier discovery
Checks for the presence of these in order, runs all that exist:
- test runner (detected from package.json scripts, Makefile, pyproject.toml, etc.)
- type checker (tsc, mypy, pyright, etc.)
- linter (eslint, ruff, golangci-lint, etc.)
- static analysis (semgrep, bandit, gosec, etc.)
- secret scanner (trufflehog, gitleaks, etc.)
- dependency/security audit (npm audit, pip-audit, cargo audit, etc.)
- repo-specific verifiers (from `.pr-review/verifiers.json` if present)

### Output schema
```json
{
  "verifiers": [{
    "name": str,
    "status": "pass" | "fail" | "warn" | "skipped" | "timeout",
    "findings": [{ "file": str, "line": int, "message": str, "severity": str }],
    "duration_ms": int
  }],
  "summary": { "passed": int, "failed": int, "warnings": int, "skipped": int }
}
```

---

## `map_diff_hotspots.py`
Marks likely attention zones in the diff. These are areas where reviewers should spend disproportionate attention — not findings themselves, but focus magnets.

### Inputs
- parsed diff (from `collect_pr_context.py`)
- risk classification (from `classify_change_risk.py`)

### Hotspot detection patterns
Pattern-match against the diff for:
- permission/authorization checks (role checks, ACL logic, `can_`, `is_authorized`, `has_permission`)
- serialization boundaries (JSON encode/decode, protobuf, API request/response shaping)
- null/error handling (catch blocks, nil checks, Optional unwrapping, error returns)
- retries and timeouts (retry loops, backoff, timeout config, deadline propagation)
- cache invalidation (cache.delete, cache.clear, TTL changes, cache key construction)
- feature flag checks (flag evaluation, flag-gated branches, rollout percentage)
- data migrations (schema changes, data transforms, backfill logic)
- SQL or query construction (especially dynamic queries, string interpolation in queries)
- cryptographic operations (hashing, signing, token generation, key management)
- external service calls (HTTP clients, SDK calls, queue producers/consumers)

### Output
Per hotspot:
- file and line range
- hotspot category
- why it matters in one sentence
- risk lane context (is this hotspot part of why the PR is yellow/red?)

---

## `check_required_artifacts.py`
Flags missing review-support artifacts. What's required depends on the risk lane — green-lane changes need almost nothing, red-lane changes need everything.

### Inputs
- PR context (from `collect_pr_context.py`)
- risk classification (from `classify_change_risk.py`)
- repo-specific artifact config (from `.pr-review/required-artifacts.json` if present)

### Default artifact requirements by lane

#### Green
- linked issue or PR description explaining why (recommended, not required)

#### Yellow
- linked issue or PR description explaining why (required)
- tests covering the changed behavior (required if test files exist for the area)
- changelog entry (if repo has a changelog convention)

#### Red
- linked issue or PR description explaining why (required)
- tests covering the changed behavior (required)
- migration/rollback guidance (required for migration changes)
- rollout note (required for rollout-sensitive changes)
- security review note (required for auth/secrets/trust-boundary changes)

### Output
Per missing artifact:
- what's missing
- why it's required for this lane
- where it should go (file path or PR section)

---

## `dedupe_findings.py`
Collapses repeated findings from tools and reviewers into one canonical finding.

### Deduplication strategy
- exact match: same file, same line range, same issue → merge, keep strongest evidence
- semantic overlap: different wording, same underlying issue → merge, cite both sources
- corroboration: multiple independent sources flag the same area → boost confidence, note agreement
- conflict: two reviewers disagree on the same code → surface both positions, mark as contested for human judgment

### Output
Deduplicated finding list where each finding includes:
- canonical description
- all contributing sources (verifier, fresh-eyes, challenger)
- merged confidence (boosted if corroborated, noted if contested)
- evidence chain

---

## `build_reviewer_packet.py`
Builds the final human-readable packet from all artifacts. This is what the human reviewer actually sees — it must be scannable in under 30 seconds for green-lane, under 2 minutes for red-lane.

### Packet structure
```
## PR Review Packet
### TL;DR
[1-2 sentence summary: what changed, risk lane, top concern if any]

### Risk: [GREEN | YELLOW | RED]
Contributing factors: [bulleted list]
AI-assisted: [yes/no, tools detected]

### Verification Status
[table: verifier name | status | notable findings]

### Findings ([N] items)
[ordered by severity × confidence]
Each finding:
  - title
  - file:line
  - why it matters
  - evidence type and source
  - suggested action: fix | verify | discuss

### Unresolved Assumptions
[things the tile couldn't determine — questions for the human]

### Recommended Review Focus
[specific files/hunks where human attention is most needed and why]

### Metadata
- reviewer mode: fresh_eyes | challenger | aggregated
- reviewer model family
- authoring model family (if detected)
- wall-clock time
- context isolation: yes/no
```

---

## `record_review_outcomes.py`
Collects retrospective outcomes from GitHub API for evals and iteration.

### Responsibilities
- query GitHub PR review comments for resolution state
- query PR timeline for merge timing and review rounds
- search for post-merge issues linked to the PR
- parse commit trailers for AI authorship signals
- write structured outcome record for the eval pipeline

### Data flow
- runs on demand via `review-retrospective` skill invocation (e.g. "how did PR #6 go?")
- reads: PR number, repo, tile finding IDs
- writes: JSON outcome record per PR with per-finding disposition

---

## `detect_ai_authorship.py`
Determines whether a PR was AI-assisted by inspecting commit metadata.

### Detection method
Parse `Co-Authored-By` trailers from all commits in the PR branch.

```
git log --format='%(trailers:key=Co-Authored-By)' origin/main..HEAD
```

Known AI co-author patterns:
- `Co-Authored-By: Claude` (Claude Code, Claude via IDE)
- `Co-Authored-By: Copilot` (GitHub Copilot)
- `Co-Authored-By: Cursor` (Cursor AI)
- Other `Co-Authored-By` entries matching known AI tool signatures

### Output
- `ai_assisted: true | false`
- `ai_tools_detected: ["claude", ...]`
- `ai_commit_ratio: float` (fraction of PR commits with AI co-author)

### Design notes
- This is metadata-based, not heuristic. If the commit says it was AI-assisted, we believe it. If it doesn't, we don't guess.
- Teams using AI tools that don't add `Co-Authored-By` trailers will show as human-authored. That's acceptable — false negatives are fine, false positives are not.

---

## Rules spec

## Rule: `review-boundaries`
The tile must never:
- approve a PR
- block a PR as final authority
- claim a finding is definitive without evidence
- pretend to know intent it was not given
- generate a "LGTM" or approval-equivalent signal
- post a summary that could be mistaken for a sign-off

Every tile output must include an explicit disclaimer: this is an evidence-based review aid, not an approval. The tile produces findings and questions. Humans produce decisions.

Violation test: if a developer could read the tile's output and conclude "the AI approved this, I don't need to look," the output violates this rule.

## Rule: `reviewer-independence`
The tile must:
- prefer independent reviewer contexts over same-context self-review
- mark whether review was same-model or challenger-mode
- avoid reading the authoring chain
- report context isolation status honestly in provenance metadata

### Implementation: preferred (structural isolation)
Run reviewer skills in a separate agent session that receives only the evidence pack and raw diff. The reviewing agent does not receive the authoring prompt, the authoring agent's reasoning, or the authoring session's tool call history. This is real context isolation. Report `context_isolation: true`.

### Implementation: fallback (soft isolation)
Because Tessl skills within a tile share the same context window, structural isolation requires a separate agent session. If a separate session is not available or not supported by the runtime, the tile falls back to soft isolation:
- the reviewer skill's instructions scope it to the evidence pack only
- the reviewer is instructed to base findings solely on the pack and raw diff
- provenance reports `context_isolation: false`
- the reviewer packet includes a note that isolation was instructional, not structural

The tile should attempt structural isolation first and degrade to soft isolation automatically.

### Provenance metadata on every review output:
- `reviewer_mode: fresh_eyes | challenger`
- `reviewer_model_family: string`
- `context_isolation: true | false`
- `authoring_model_family: string | unknown`

## Rule: `evidence-threshold`
A surfaced finding must include at least one of:
- deterministic verifier output (test failure, lint error, type error, security scan hit)
- concrete hunk-level code evidence (specific line, specific problem, specific consequence)
- repo-instruction or policy conflict (citable rule from repo config, CODEOWNERS, or contributing guide)
- explicit contextual reasoning tied to changed code (cross-reference with existing code that creates the problem)

Findings that don't meet this bar are handled as follows:
- if the reviewer has moderate confidence: downgrade to a question ("worth checking: does X handle Y?")
- if the reviewer has low confidence: suppress entirely
- never surface a finding whose only evidence is "this looks like it might be wrong"

Every surfaced finding must include its evidence type so the human reviewer can assess trust calibration.

## Rule: `comment-quality`
The tile must:
- prefer hunk-level comments tied to specific lines
- suppress generic style advice (especially if a linter already covers it)
- avoid repetitive phrasing across findings — each finding gets its own language
- explain impact, not just code difference ("this can cause X" not "this was changed from Y to Z")
- never generate comments that require the reviewer to read more than the finding itself to understand the issue

Anti-patterns to actively suppress:
- "Consider using..." without explaining what breaks if you don't
- "This could be improved by..." without a concrete defect or risk
- "Nitpick:" anything — if it's not worth fixing, it's not worth saying
- Restating the diff in English ("this function was renamed from X to Y")
- Boilerplate praise ("good use of...", "nice refactoring...")

All findings that clear the evidence threshold are surfaced. There is no arbitrary cap. The evidence threshold IS the volume control.

## Rule: `risk-routing`
The tile must:
- route green changes through the lightest viable workflow (evidence + 1 review pass + synthesis)
- route yellow changes through standard workflow (evidence + review + optional challenger + synthesis + handoff)
- escalate red changes to full workflow with mandatory human review
- use challenger review selectively based on risk lane or reviewer uncertainty
- never skip the evidence-build stage regardless of risk lane

When the risk classifier's confidence is low, route to the next higher lane. False red is cheap. False green is dangerous.

Performance routing:
- green: synchronous, under 2 minutes
- yellow: synchronous, under 5 minutes
- red: may run async, under 10 minutes, notifies when ready

## Rule: `human-escalation`
The tile must explicitly escalate to mandatory human review:
- architecture shifts (new subsystems, changed boundaries, new dependencies)
- public API changes (REST routes, GraphQL schema, proto files, exported types)
- migrations (database schema, data migrations, config migrations)
- rollout-sensitive changes (feature flags, gradual rollout logic, kill switches)
- auth, security, secrets, and trust-boundary logic
- changes with unresolved intent ambiguity (PR description doesn't explain why)
- multi-subsystem changes where the interaction between subsystems matters
- concurrency changes (locks, async boundaries, race conditions)

Escalation means:
- the human-review-handoff packet explicitly marks these areas
- the tile does NOT reduce its finding output for escalated areas
- the tile surfaces specific questions the human reviewer should answer
- the tile never implies that its own review is sufficient for these categories

---

## Proposed tile manifest

```json
{
  "name": "tessl-labs/pr-review-guardrails",
  "version": "0.1.0",
  "summary": "Evidence-first pull request review with independent critique, selective challenger review, and human handoff.",
  "private": true,
  "skills": {
    "pr-evidence-builder": { "path": "skills/pr-evidence-builder/SKILL.md" },
    "fresh-eyes-review": { "path": "skills/fresh-eyes-review/SKILL.md" },
    "challenger-review": { "path": "skills/challenger-review/SKILL.md" },
    "finding-synthesizer": { "path": "skills/finding-synthesizer/SKILL.md" },
    "human-review-handoff": { "path": "skills/human-review-handoff/SKILL.md" },
    "review-retrospective": { "path": "skills/review-retrospective/SKILL.md" }
  },
  "rules": {
    "review-boundaries": { "rules": "rules/review-boundaries.md" },
    "reviewer-independence": { "rules": "rules/reviewer-independence.md" },
    "evidence-threshold": { "rules": "rules/evidence-threshold.md" },
    "comment-quality": { "rules": "rules/comment-quality.md" },
    "risk-routing": { "rules": "rules/risk-routing.md" },
    "human-escalation": { "rules": "rules/human-escalation.md" }
  }
}
```

---

## Suggested configuration knobs

### Reviewer strategy
- `review_strategy: preflight_only | same_model | challenger | aggregated`

### Challenger strategy
- `challenger_mode: off | same_family | cross_family | auto`

### Risk thresholds
- `enable_challenger_on: yellow | red`
- `mandatory_human_on: red`

### Finding surfacing
- `suppress_below_evidence_threshold: true`
- `suppress_style_if_linter_covers: true`
- No arbitrary finding caps. Every finding that clears the evidence threshold is surfaced. The threshold is the filter — not a number.

### Verification policy
- `require_verifier_support_for_high_confidence: true`

### Performance budgets
Wall-clock targets per risk lane. If the tile is slower than a developer's context-switch threshold, they'll skip it.
- `green_lane_budget_seconds: 120` (under 2 minutes — before the developer moves on)
- `yellow_lane_budget_seconds: 300` (under 5 minutes — acceptable for substantive changes)
- `red_lane_budget_seconds: 600` (under 10 minutes — justified by risk, runs async)

Design implications:
- Evidence collection and verifiers run in parallel, not sequentially
- Green-lane: 1 review pass + synthesis. No challenger.
- Yellow-lane: 1 review + optional challenger + synthesis. Challenger runs in parallel with primary review when possible.
- Red-lane: full pipeline. Acceptable to run async and notify when ready.
- Evidence packs are cached. Re-reviews after force-push rebuild only the changed portions.

### Provenance capture
- `capture_authoring_mode: true`
- `capture_reviewer_mode: true`
- `capture_outcomes_for_eval: true`

---

## Evaluation plan
The tile should be evaluated in four modes on the same PR corpus:

1. Human-only baseline
2. Independent same-model review
3. Independent challenger review
4. Aggregated review with synthesis and human handoff

### Core metrics
- valid finding precision
- false positives per PR
- unique valid findings beyond baseline
- signal-to-noise ratio
- comment adoption rate
- reviewer time spent
- time to merge
- escaped defects
- developer trust

### Important segmentation
Track separately for:
- human-authored PRs
- mixed-authorship PRs
- heavily AI-authored PRs
- pre-PR versus PR-stage review
- green/yellow/red risk lanes
- same-model versus cross-model challenger mode

---

## Open questions
1. Which repositories have enough verifier maturity to support evidence-first review?
2. What signal from the primary reviewer constitutes "low confidence" sufficient to trigger challenger review automatically? (The spec gates challenger on both risk lane and reviewer uncertainty, but the confidence threshold is undefined — is it a self-reported field, a ratio of low-confidence findings, or an explicit reviewer statement?)
3. How should the tile expose unresolved assumptions without becoming verbose?

---

## Recommended next deliverables
1. Draft `tile.json`
2. Draft the 6 rules files
3. Draft `SKILL.md` for all 6 skills
4. Design the first eval corpus and scorecard

