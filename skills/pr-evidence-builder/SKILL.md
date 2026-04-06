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

## Inputs

- PR diff or branch diff
- PR title and description
- Linked issue or task (if available)
- Repository instructions (if available)

## Critical: always produce output

The pipeline steps below are best-effort guidance. If any step fails or is not possible (missing tools, API errors, permission issues), skip it and proceed. **You must always produce a review with findings, even if some pipeline steps could not be completed.** Write output early and incrementally. An empty output directory is always a failure — at minimum write the evidence pack JSON and a review markdown with whatever findings you have.

## Steps

Perform each step using available tools (gh CLI, git, file reading, etc.). If a helper script from the tile's `scripts/` directory is available in the working directory, prefer it. Otherwise, perform the step directly — do not fail or stop if a script is missing.

1. **Check diff size.** Count the total lines changed. If the diff exceeds 1,000 lines changed, surface a blocker: "this PR is too large for effective review — consider splitting into smaller PRs." Still run verifiers and produce a partial evidence pack, but skip the AI review passes (fresh-eyes, challenger). If the diff is between 500–1,000 lines, note the size as a risk factor but proceed.

2. **Collect PR context.** Using `gh` and `git` commands, gather:
   - PR title, description, labels, and linked issues — e.g., `gh pr view $PR --json title,body,labels,files`
   - Diff metadata: files changed, insertions, deletions, renames — e.g., `git diff --stat origin/main...HEAD`
   - Touched files with change type (added, modified, deleted, renamed)
   - Subsystem clusters inferred from directory structure or CODEOWNERS
   - Related test files (by naming convention: `foo.py` → `test_foo.py`)
   - Code owners from CODEOWNERS if present
   - AI authorship: check `Co-Authored-By` commit trailers for known AI tool names (Claude, Copilot, Cursor)

   If GitHub API is unreachable, produce a partial evidence pack from local git data. Mark unavailable fields as null.

3. **Run deterministic verifiers.** Discover and invoke repo-native tools that are present:
   - Test runner (from package.json, pyproject.toml, Makefile, go.mod, Cargo.toml) — e.g., `jq -r '.scripts.test' package.json` to find the test command, then `timeout 60 npm test 2>&1` to run it
   - Type checker (tsc, mypy, pyright) — e.g., `timeout 60 npx tsc --noEmit 2>&1`
   - Linter (eslint, ruff, golangci-lint, clippy)
   - Static analysis (semgrep, bandit, gosec)
   - Secret scanner (gitleaks, trufflehog)
   - Dependency audit (npm audit, pip-audit, cargo audit)
   - Repo-specific verifiers from `.pr-review/verifiers.json` if present

   Capture each verifier's status (pass/fail/warn/skipped/timeout) and findings. Enforce a 60-second timeout per verifier. If no verifiers are discovered, note this and proceed.

4. **Classify risk.** Assign a risk lane based on what the PR touches. Check for repo-specific overrides in `.pr-review/risk-overrides.json`. Check the PR description for an explicit risk override (`risk: red`) — overrides can escalate only, never downgrade. When confidence is low, round UP to the next higher lane.

   | Lane | Applies when |
   |------|-------------|
   | **Green** | Docs-only, test-only, safe renames, formatting. Pure renames/import reorders with no logic change are green even in sensitive directories. |
   | **Yellow** | Business logic, moderate refactors, non-public API changes, config with bounded blast radius. Auth/permission refactors that do **not** alter the effective access policy (e.g., reorganizing checks, renaming guards, switching between semantically equivalent implementations) — classify yellow, not red, when call-site analysis confirms the access policy is preserved. |
   | **Red** | Auth/permission changes that **alter who can access what**, migrations, public API changes, infra/deploy, secrets/trust boundaries, concurrency, cache invalidation (especially when caching authorization-relevant data), rollout/feature flags, multi-subsystem changes. |

   **Auth risk requires call-site analysis.** Do not classify a PR as red solely because it touches permission-checking code. Read the call sites to determine whether the effective access policy changed. For example, a switch from `every()` to `some()` on a role array changes behavior — but if every call site passes OR-style role lists, `some()` is the correct semantic and the change is a bug fix, not a regression. Classify based on whether the access policy actually changed.

5. **Map hotspots.** Scan the diff for attention-worthy patterns and flag each occurrence:
   - Permission/authorization checks
   - Serialization boundaries (JSON, protobuf, API shaping)
   - Null/error handling (catch blocks, nil checks, Optional)
   - Retries and timeouts
   - Cache invalidation — especially when cached data includes authorization-relevant fields (roles, permissions, access levels, scopes), which creates a window where revocation or downgrade is invisible
   - Feature flag checks
   - Data migrations and schema changes
   - SQL or query construction (especially dynamic/interpolated queries)
   - Cryptographic operations
   - External service calls
   - Output encoding — CSV/spreadsheet exports where user data can reach cells interpreted as formulas
   - Shared resource contention — health checks acquiring DB pool connections, in-memory state in multi-process deployments, connection pool sizing under concurrent load
   - Infrastructure lifecycle — storage tier transitions, backup retention policies, availability zone placement, replication configuration

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
