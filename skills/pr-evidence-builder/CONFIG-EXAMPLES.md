# Configuration Examples

All configuration files live in `.pr-review/` at the repository root. All are optional — the tile has sensible defaults without any of them.

## `verifiers.json`

Define custom verification commands beyond what the tile auto-discovers.

```json
[
  {
    "name": "contract-tests",
    "command": "npm run test:contracts",
    "timeout_ms": 90000
  },
  {
    "name": "openapi-validate",
    "command": "npx @stoplight/spectral-cli lint openapi.yaml",
    "timeout_ms": 30000
  },
  {
    "name": "db-schema-check",
    "command": "python scripts/validate_schema.py --check-pending",
    "timeout_ms": 60000
  }
]
```

Each entry:
- `name` (required): human-readable verifier name, appears in the evidence pack and reviewer packet
- `command` (required): shell command to run from repo root
- `timeout_ms` (optional): per-verifier timeout in milliseconds, defaults to 60000

The command should exit 0 on success, non-zero on failure. Output to stdout/stderr is captured and parsed for findings.

## `risk-overrides.json`

Force specific path patterns to a minimum risk lane. Overrides can only escalate, never downgrade.

```json
[
  {
    "pattern": "billing/",
    "lane": "red"
  },
  {
    "pattern": "internal-tools/",
    "lane": "yellow"
  },
  {
    "pattern": "\\.env\\.",
    "lane": "red"
  },
  {
    "pattern": "api/v[0-9]+/",
    "lane": "red"
  }
]
```

Each entry:
- `pattern` (required): regex pattern matched against touched file paths (case-insensitive)
- `lane` (required): `"yellow"` or `"red"` — the minimum lane for files matching this pattern

If a file matches a red override but the classifier says green, the file is escalated to red. If the classifier already says red, the override has no effect.

## `subsystems.json`

Explicit subsystem map for repos where directory structure and CODEOWNERS are insufficient.

```json
{
  "api": ["src/api/**", "src/routes/**"],
  "worker": ["src/worker/**", "src/jobs/**"],
  "auth": ["src/auth/**", "src/middleware/auth*"],
  "billing": ["src/billing/**", "src/stripe/**"],
  "frontend": ["web/**", "src/components/**"]
}
```

Keys are subsystem names. Values are glob patterns matched against touched file paths. A file matching multiple subsystems is assigned to the first match.

This map feeds directly into risk classification — if a PR touches files in 3+ subsystems, the "multi-subsystem" red factor triggers.

## `required-artifacts.json`

Override default artifact requirements per risk lane.

```json
{
  "green": [
    {
      "artifact": "PR description or linked issue",
      "check": "has_intent",
      "required": false,
      "why_required": "Recommended: helps reviewers understand why"
    }
  ],
  "yellow": [
    {
      "artifact": "PR description or linked issue",
      "check": "has_intent",
      "required": true,
      "why_required": "Required: reviewers need motivation context"
    },
    {
      "artifact": "Tests covering changed behavior",
      "check": "has_tests",
      "required": true,
      "why_required": "Required: changed behavior must be verified"
    }
  ],
  "red": [
    {
      "artifact": "PR description or linked issue",
      "check": "has_intent",
      "required": true,
      "why_required": "Required: high-risk changes need clear documentation"
    },
    {
      "artifact": "Tests covering changed behavior",
      "check": "has_tests",
      "required": true,
      "why_required": "Required: high-risk changes need test coverage"
    },
    {
      "artifact": "Migration/rollback guidance",
      "check": "has_migration_guidance",
      "required": true,
      "why_required": "Required for migrations: rollback plan must exist"
    },
    {
      "artifact": "Security review note",
      "check": "has_security_note",
      "required": true,
      "why_required": "Required for auth changes: security review documented"
    }
  ]
}
```

Available check types: `has_intent`, `has_tests`, `has_changelog`, `has_migration_guidance`, `has_rollout_note`, `has_security_note`.
