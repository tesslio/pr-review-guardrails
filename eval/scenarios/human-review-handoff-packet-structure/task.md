# Generate PR Review Packet for Database Migration PR

## Problem/Feature Description

Your team's automated review pipeline has completed its analysis on a pull request that introduces a significant database schema migration alongside changes to a public REST API. The pipeline has produced a synthesized set of findings. Now you need to produce the final document that the human reviewer — a senior engineer who is not familiar with the PR — will actually read when they sit down to do their approval decision.

The human reviewer has limited time. For high-risk changes they need everything surfaced clearly and efficiently, not buried in logs or raw JSON. The reviewer needs to know exactly where to look, what questions remain unanswered, and what the automated analysis verified. Any areas that require mandatory human attention (rather than just a scan) must be called out explicitly.

## Output Specification

Produce a single file: `review-packet.md`

This is the complete reviewer document. It must contain all sections needed for the human reviewer to understand the PR, triage the findings, and know where to focus attention. Do not produce a JSON file — produce a formatted markdown document intended for a human reader.

## Input Files

The following files are provided as inputs. Extract them before beginning.

=============== FILE: inputs/synthesized-findings.json ===============
{
  "findings": [
    {
      "finding_id": "f-001",
      "title": "Column NOT NULL added without migration default — will fail on non-empty tables",
      "file": "db/migrations/0042_add_user_tier.sql",
      "line_start": 8,
      "line_end": 8,
      "hunk": "ALTER TABLE users ADD COLUMN tier VARCHAR(20) NOT NULL;",
      "why_it_matters": "PostgreSQL rejects adding a NOT NULL column with no DEFAULT to a table that already has rows. This migration will fail in production where the users table is non-empty, potentially causing downtime.",
      "evidence": {"type": "hunk_level_code", "detail": "No DEFAULT clause on line 8; production users table has 2.1M rows per ops dashboard."},
      "confidence": "high",
      "severity": "critical",
      "action": "fix",
      "requires_human": true,
      "corroborated_by": ["fresh_eyes", "challenger"],
      "contested_by": [],
      "merged_confidence": "high",
      "suppressed": false
    },
    {
      "finding_id": "f-002",
      "title": "New /v2/users endpoint returns internal user IDs in response body",
      "file": "src/api/users_v2.py",
      "line_start": 67,
      "line_end": 72,
      "hunk": "return jsonify({'id': user.internal_id, 'email': user.email, 'tier': user.tier})",
      "why_it_matters": "Exposing internal database IDs in a public API creates an enumeration attack surface and may leak information about record counts and insertion order to external callers.",
      "evidence": {"type": "hunk_level_code", "detail": "user.internal_id is the auto-increment PK; the previous v1 endpoint used a UUID slug."},
      "confidence": "high",
      "severity": "high",
      "action": "verify",
      "requires_human": true,
      "corroborated_by": ["fresh_eyes"],
      "contested_by": [],
      "merged_confidence": "high",
      "suppressed": false
    },
    {
      "finding_id": "f-003",
      "title": "No test coverage for migration rollback path",
      "file": "db/migrations/0042_add_user_tier.sql",
      "line_start": null,
      "line_end": null,
      "hunk": null,
      "why_it_matters": "If the migration must be rolled back in production, the absence of a tested rollback path increases mean time to recovery.",
      "evidence": {"type": "verifier_output", "detail": "Test coverage report shows 0% coverage for rollback scripts; migration file contains no DOWN migration."},
      "confidence": "medium",
      "severity": "medium",
      "action": "discuss",
      "requires_human": false,
      "corroborated_by": ["fresh_eyes"],
      "contested_by": [],
      "merged_confidence": "medium",
      "suppressed": false
    }
  ],
  "missing_sources": [],
  "synthesis_metadata": {"deduplication_applied": true, "suppressed_count": 2}
}

=============== FILE: inputs/evidence-pack-summary.json ===============
{
  "pr": 247,
  "title": "Add user tier system with DB migration and v2 API endpoint",
  "risk": {"lane": "red", "confidence": "high", "factors": ["database schema migration", "public API change", "new subsystem interaction"]},
  "authorship": {"ai_assisted": false},
  "verification": [
    {"verifier": "pytest", "status": "pass", "finding_count": 0},
    {"verifier": "mypy", "status": "pass", "finding_count": 0},
    {"verifier": "flake8", "status": "pass", "finding_count": 0},
    {"verifier": "pip-audit", "status": "pass", "finding_count": 0}
  ],
  "subsystems": ["database", "api"],
  "reviewer_metadata": {
    "reviewer_mode": "aggregated",
    "reviewer_model_family": "claude-3",
    "authoring_model_family": "unknown",
    "context_isolation": true,
    "wall_clock_seconds": 94
  }
}
