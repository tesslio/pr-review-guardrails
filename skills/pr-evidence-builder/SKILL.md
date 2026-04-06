---
name: pr-evidence-builder
description: |
  Build a compact, trustworthy evidence pack before deeper PR review starts.
  Use this skill when a pull request needs review — it is always the first step.
  Triggered by requests to review code, check a PR, review my changes, review a merge request,
  or any similar code review or pull request review request.
  Collects PR context, runs deterministic verifiers, classifies risk, maps hotspots,
  and checks for missing artifacts. Produces the evidence pack that all downstream
  review skills consume.
---

# PR Evidence Builder

Build the evidence pack that powers all downstream review. This skill runs first, always.

## When to use

- A pull request is opened or updated and needs review
- An author wants preflight feedback before opening a PR
- Any time the tile is invoked — this skill is the entry point

## Inputs

- PR diff or branch diff
- PR title and description
- Linked issue or task (if available)
- Repository instructions (if available)

## Critical: always produce output

The pipeline steps below are best-effort guidance, not a mandatory sequential gate. If any step fails or is not possible (missing tools, API errors, permission issues), skip it and proceed with the next step. **You must always produce a review with findings, even if some pipeline steps could not be completed.** A partial evidence pack with a good review is infinitely better than no output. Never spend more than a few attempts on a failing step — move on.

**Write output early and incrementally.** Do not accumulate all findings in memory and write them at the end. Write your evidence pack and review findings to output files as soon as you have them — even partial results. A partial review is infinitely better than no review.

**Failure mode:** If you reach the end of the pipeline and have not written any output files, you have failed. Before that happens — at minimum write the evidence pack JSON with whatever data you have, and the review markdown with whatever findings you have. Even a review that says "evidence pack construction partially failed; here are findings from manual diff reading" is a success. An empty output directory is always a failure.

## Steps

Perform each step using available tools (gh CLI, git, file reading, etc.). If a helper script from the tile's `scripts/` directory is available in the working directory, prefer it. Otherwise, perform the step directly — do not fail or stop if a script is missing.

1. **Check diff size.** Count the total lines changed. If the diff exceeds 1,000 lines changed, surface a blocker: "this PR is too large for effective review — consider splitting into smaller PRs." Still run verifiers and produce a partial evidence pack, but skip the AI review passes (fresh-eyes, challenger). If the diff is between 500–1,000 lines, note the size as a risk factor but proceed.

2. **Collect PR context.** Using `gh` and `git` commands, gather:
   - PR title, description, labels, and linked issues
   - Diff metadata: files changed, insertions, deletions, renames
   - Touched files with change type (added, modified, deleted, renamed)
   - Subsystem clusters inferred from directory structure or CODEOWNERS
   - Related test files (by naming convention: `foo.py` → `test_foo.py`)
   - Code owners from CODEOWNERS if present
   - AI authorship: check `Co-Authored-By` commit trailers for known AI tool names (Claude, Copilot, Cursor)

   If GitHub API is unreachable, produce a partial evidence pack from local git data. Mark unavailable fields as null.

3. **Run deterministic verifiers.** Discover and invoke repo-native tools that are present:
   - Test runner (from package.json, pyproject.toml, Makefile, go.mod, Cargo.toml)
   - Type checker (tsc, mypy, pyright)
   - Linter (eslint, ruff, golangci-lint, clippy)
   - Static analysis (semgrep, bandit, gosec)
   - Secret scanner (gitleaks, trufflehog)
   - Dependency audit (npm audit, pip-audit, cargo audit)
   - Repo-specific verifiers from `.pr-review/verifiers.json` if present

   Capture each verifier's status (pass/fail/warn/skipped/timeout) and findings. Enforce a 60-second timeout per verifier. If no verifiers are discovered, note this and proceed.

4. **Classify risk.** Assign a risk lane based on what the PR touches:
   - **Green:** docs-only, test-only, safe renames (even in sensitive directories — if every change is purely a rename or import reorder with no logic change, it is green), formatting
   - **Yellow:** business logic, moderate refactors, non-public API changes, config with bounded blast radius, **refactors of auth/permission code that do not change the effective access policy** (e.g., reorganizing permission checks, renaming guards, switching between semantically equivalent implementations — classify as yellow, not red, if you verify the access policy is preserved by reading call sites)
   - **Red:** auth/permissions changes that **alter who can access what**, migrations, public API changes, infra/deploy, secrets/trust boundaries, concurrency, cache invalidation (especially when caching authorization-relevant data like roles or permissions), rollout/feature flags, multi-subsystem changes

   **Auth risk classification requires call-site analysis.** Do not classify a PR as red solely because it touches permission-checking code. Read the call sites to determine whether the effective access policy changed. A function that switches from `every()` to `some()` on a role array changes behavior — but if every call site passes OR-style role lists (e.g., `['admin', 'manager']`), then `some()` is the correct semantic and the change is a bug fix, not a regression. Classify based on whether the access policy actually changed, not on whether the code is in an auth-related file.

   When confidence is low, round UP to the next higher lane. Check for repo-specific overrides in `.pr-review/risk-overrides.json`. Check the PR description for explicit risk override (`risk: red`) — overrides can escalate only, never downgrade.

5. **Map hotspots.** Scan the diff for attention-worthy patterns:
   - Permission/authorization checks
   - Serialization boundaries (JSON, protobuf, API shaping)
   - Null/error handling (catch blocks, nil checks, Optional)
   - Retries and timeouts
   - Cache invalidation — especially when cached data includes authorization-relevant fields (roles, permissions, access levels, scopes). Caching authorization state creates a window where revocation or downgrade is invisible.
   - Feature flag checks
   - Data migrations and schema changes
   - SQL or query construction (especially dynamic/interpolated queries)
   - Cryptographic operations
   - External service calls
   - Output encoding — CSV generation, spreadsheet exports, file downloads where user data reaches cells that can be interpreted as formulas
   - Shared resource contention — health checks that acquire DB pool connections, in-memory state (dedup sets, caches) in multi-process deployments, connection pool sizing under concurrent load
   - Infrastructure lifecycle — storage tier transitions (Glacier, archive tiers with retrieval delays), backup retention policies, availability zone placement, replication configuration

6. **Check required artifacts.** Based on the risk lane, flag missing items:
   - **Green:** PR description recommended but not required
   - **Yellow:** PR description required, tests required if test files exist for the area
   - **Red:** PR description required, tests required, migration/rollback guidance for migrations, rollout note for rollout changes, security review note for auth/secrets changes

7. **Compose evidence pack.** Merge all outputs into a structured JSON evidence pack (see `SCHEMA.md`). This is the single input to all review skills.

## Outputs

- Machine-readable evidence pack (JSON, schema version 1.0 — see `SCHEMA.md`)
- Concise summary for later reviewers
- Blocker if diff is oversized (>1,000 lines)

## Success criteria

- Reviewers receive enough context to avoid shallow generic feedback
- Missing artifacts are surfaced before human review starts
- Oversized diffs are caught early with an actionable split recommendation
