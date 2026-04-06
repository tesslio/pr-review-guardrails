---
name: fresh-eyes-review
description: |
  Provide an independent critique of a pull request (PR) using a clean reviewer context,
  identifying bugs, security issues, code quality problems, API misuse, and missing test
  coverage. Use when performing a code review or pull request review after an evidence pack
  has been built, for green or yellow risk lane PRs, or as part of a full pipeline for red
  risk lane PRs. Produces candidate findings (covering correctness, security, and
  architectural concerns) for downstream synthesis — not final verdicts. Operates as a
  critic, not a co-author. Common triggers: "review this PR", "code review feedback",
  "fresh review", "independent review".
---

# Fresh-Eyes Review

Independent critique of a pull request from a clean reviewer context.

## When to use

- After `pr-evidence-builder` has produced an evidence pack
- For green and yellow risk lane PRs (always)
- For red risk lane PRs (as part of the full pipeline)

## Rules

- Must not run in the same context as code generation (see `reviewer-independence` rule — e.g. `.github/review-rules/reviewer-independence.md`)
- Must behave as critic, not co-author
- Must produce candidate findings, not verdicts
- Base all findings solely on the evidence pack and raw diff

## Inputs

- Evidence pack from `pr-evidence-builder` (see `skills/pr-evidence-builder.md`)
- Raw diff

Do NOT use any other context. Do not read authoring prompts, agent reasoning, or tool call history from the authoring session.

### Evidence pack structure (expected fields)

A valid evidence pack typically contains:
- `risk_lane`: green | yellow | red
- `changed_files`: list of file paths touched
- `subsystems`: list of subsystems affected
- `hotspots`: list of high-risk file/line areas flagged by verifiers
- `verifier_output`: structured results from automated checks (linting, tests, security scans)
- `stated_intent`: description of what the PR is supposed to do

> If any of these fields are missing or empty, note the gap in your output but proceed with what is available. Do not block on an incomplete evidence pack — flag the limitation as a low-confidence contextual finding.

## Priority: precision over thoroughness

Spend your effort on finding the most important issues, not on being comprehensive. A review with 2 precise, well-grounded findings is better than one with 8 findings that includes noise. Read the diff carefully, identify what actually matters, and stop. Do not pad the review with low-value observations.

**Write findings as you go.** Do not wait until you have reviewed the entire diff to start producing output. Write each finding as you discover it.

## Steps

1. **Read the evidence pack.** Understand what changed, which subsystems are touched, what the risk lane is, what the verifiers found, and where the hotspots are.

2. **Review the raw diff.** Focus attention on hotspots and risk-contributing areas first. Review in this priority order — security issues first, because they are most likely to be high-severity:
   - Security issues (injection, auth bypass, secret exposure, unsanitized input reaching response headers or logs, CRLF injection, CSV formula injection, output encoding)
   - Correctness problems (null handling, off-by-one, missing error paths, type mismatches after deserialization)
   - API misuse or contract violations
   - Authorization/cache interaction (when caching stores permission-relevant data — roles, access levels, scopes — any revocation or downgrade is invisible until TTL expires)
   - Resource contention and cascading failures (shared connection pools, thread/process isolation, load balancer feedback loops)
   - Infrastructure and operational risks (storage tier transitions that break access patterns, replication that doesn't provide HA, missing backups, retention policies set to zero)
   - Defensive coding gaps
   - Missing test coverage for changed behavior
   - Logic that contradicts the stated intent

   When untrusted input (request headers, query params, body fields) flows to any output channel (response headers, logs, database queries, downstream calls, **CSV/spreadsheet exports**, file downloads), trace the full path. Each output channel is a separate potential issue — do not collapse them into one finding. Sanitization that protects one channel does not protect another (e.g., JSON escaping protects log output but does not prevent HTTP header injection via the same value). **If you identify an unsanitized input flow, emit it as a finding** — do not merely mention it in the TL;DR or risk summary. An observation that doesn't become a finding is invisible to downstream synthesis.

   **CSV and spreadsheet output:** When user-controlled data is written to CSV or spreadsheet files, check whether cell values starting with `=`, `+`, `-`, `@`, `\t`, or `\r` are sanitized. Unsanitized values are interpreted as formulas by Excel and Google Sheets, enabling command execution on the user's machine. This is a high-severity injection vulnerability.

   **Infrastructure changes:** When reviewing Terraform, CloudFormation, or infrastructure-as-code, evaluate operational consequences — not just syntactic correctness. Storage tier transitions (e.g., S3 to Glacier) introduce retrieval delays of hours that break on-demand access. Replicas in the same AZ as the primary provide no high-availability benefit — check `availability_zones` to confirm placement differs from the primary. Backup retention set to zero means no point-in-time recovery. `apply_immediately = true` on a production database means changes take effect now rather than during maintenance windows — combined with destructive changes like engine swaps, this is critical. When a Terraform resource has its engine changed (e.g., MySQL to PostgreSQL), Terraform will **destroy and recreate** the resource, deleting all data — this is not an in-place migration. These are concrete defects, not style preferences.

   **Cascading failure chains:** When a new code path acquires a shared resource (DB connection pool, thread pool, file descriptor), trace what happens under contention. Health checks that use the application DB pool compete with request handlers — under load, the health check may fail to acquire a connection, the load balancer marks the instance unhealthy and removes it, shifting traffic to remaining instances and worsening their pool exhaustion. Always trace the full cascade: resource contention → external observer reaction → load redistribution → wider failure. The same pattern applies to resource limit reductions: if memory/CPU limits are cut aggressively, normal load spikes trigger OOM kills → container restarts → traffic shifts to surviving instances → their limits are equally tight → fleet-wide cascading restarts.

   **Process/worker isolation:** When code uses in-memory data structures (sets, maps, caches) for cross-request state like deduplication, check whether the deployment model uses multiple worker processes (gunicorn, uwsgi, PM2 cluster, Kubernetes replicas). Each process has its own memory — an in-memory dedup set only deduplicates within a single process, not across workers. This is a correctness bug, not a performance concern.

   **Name the specific attack:** When reporting a security finding, always name the concrete attack technique, not just the generic risk category. "CRLF injection / HTTP response splitting" is actionable; "header manipulation" is not. "CSV formula injection via `=cmd` prefix" is actionable; "potential injection" is not. Specific attack names let reviewers assess severity and search for mitigation patterns.

   **Deserialization type fidelity:** When user-controlled data is parsed from strings (localStorage, cookies, query params, config files) via `JSON.parse`, `yaml.load`, or similar, check whether downstream code assumes specific types. A successfully-parsed value with the wrong type (string where number expected, null where object expected) may not throw — it silently produces `NaN`, `undefined`, or empty results in distant code paths. This is harder to catch than a parse crash and more dangerous.

3. **Produce candidate findings.** For each issue found, emit a structured finding. Only emit findings that meet the evidence threshold (see validation guidance below).

4. **Classify each finding.** Assign confidence, severity, and action recommendation.

## Evidence threshold validation

Before emitting a finding, verify all of the following:

- **Grounded**: The issue is directly traceable to a specific hunk, verifier output, or repo policy — not general intuition.
- **Non-duplicative**: The finding does not restate an issue already present in `verifier_output`.
- **Scoped**: The issue is in changed code, not pre-existing unrelated code (unless the change introduces a new call path to it).
- **Impactful**: The issue has a plausible realistic impact path (not merely theoretical).
- **Call-site verified (for permission/access changes)**: If the finding claims a permission check was weakened or authorization scope was changed, you MUST cite the call sites that demonstrate the actual impact. If the call sites show the change is semantically correct (e.g., role arrays used as OR conditions match `some()` semantics), the finding is a false positive — discard it.

If a candidate finding fails any check, downgrade its confidence or discard it. Do not emit findings that fail the "Grounded" or "Call-site verified" checks.

## Be explicit, not implicit

State conclusions directly. If a UI element is hidden but the server endpoint has no authorization check, say "hiding a UI element is not authorization — the endpoint is accessible to any authenticated user via direct API call." Do not merely note that the check is "client-side only" and leave the reader to infer the consequence.

When classifying risk, use the lane name from the risk routing rule (green, yellow, red) as the top-level label — not synonyms like "HIGH" or "CRITICAL." The lane name is the contract between the evidence builder and the review pipeline.

## Output shape per finding

- `finding_id`: UUID
- `source`: "fresh_eyes"
- `title`: concise issue description
- `file`: impacted file path
- `line_start` / `line_end`: specific lines (null if file-level)
- `hunk`: relevant code snippet (null if not applicable)
- `why_it_matters`: impact explanation, not diff restatement
- `evidence`: type (verifier_output | hunk_level_code | repo_policy | contextual_reasoning) and detail
- `confidence`: high | medium | low
- `severity`: critical | high | medium | low
- `action`: fix | verify | discuss
- `requires_human`: true if the issue needs human judgment

### Example finding (populated)

```json
{
  "finding_id": "a3f2c1d0-84bb-4e10-9abc-000011112222",
  "source": "fresh_eyes",
  "title": "Null dereference on missing user object before permission check",
  "file": "src/auth/permissionGuard.ts",
  "line_start": 42,
  "line_end": 44,
  "hunk": "const role = user.profile.role;\nif (role === 'admin') { ... }",
  "why_it_matters": "If `user` is null (e.g. unauthenticated request that bypasses the middleware), this throws before the permission gate is reached, potentially exposing a 500 error with stack trace.",
  "evidence": {
    "type": "hunk_level_code",
    "detail": "No null guard on `user` before property access at line 42; middleware that populates `user` is optional according to router config at routes/api.ts:18."
  },
  "confidence": "high",
  "severity": "high",
  "action": "fix",
  "requires_human": false
}
```

## Green lane reviews

For green-lane PRs (docs-only, test-only, safe renames, formatting), apply a lighter review. Do not flag documentation quality issues (incomplete coverage, missing package docs, style preferences) as findings — these are not defects. Only surface findings on green-lane PRs if they reveal an actual correctness or security problem introduced by the change. If the PR is correctly classified green and has no real defects, it is correct to produce zero findings.

## Semantic correctness over syntactic suspicion

Before flagging a logic change as a vulnerability, **read the call sites to determine intent**. This is mandatory for any finding about authorization logic changes.

Example: a change from `every()` to `some()` on a role check looks like a permission downgrade in isolation. But if call sites pass role arrays like `['admin', 'manager']` (meaning "admin OR manager can access this"), then `some()` is the correct semantic — `every()` was the bug (it required a user to have BOTH admin AND manager roles simultaneously, which is nonsensical). In this case, the change is a bug fix, not a regression.

**How to check:** Look at every place the permission guard component/function is invoked. If the arrays contain alternative roles (admin/manager, admin/analyst), the semantics are OR and `some()` is correct. If the arrays contain cumulative permissions (read+write, edit+approve), the semantics are AND and `every()` is correct. Do not guess — read the code.

Flagging a correct fix as a security vulnerability is worse than missing a real issue. It is a false positive that erodes reviewer trust and wastes human review time.

## Success criteria

- Fewer but sharper findings than generic review bots
- Minimal repetition
- Hunk-level feedback where possible
