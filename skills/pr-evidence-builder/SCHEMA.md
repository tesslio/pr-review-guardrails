# Evidence Pack Schema

Version: 1.0

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

## Design notes

- `raw_diff` is included so reviewer skills can inspect actual code, not just metadata. If the diff exceeds the model's usable context window, the tile should not truncate — it should block AI review and recommend splitting the PR (see `pr-evidence-builder` oversized diff handling).
- `repo_instructions` captures contributing guides, PR templates, or `.pr-review/` config that the reviewer should respect.
- The pack is self-contained. A reviewer skill should be able to produce findings from this artifact alone without making additional API calls or reading additional files.
- `schema_version` is included for forward compatibility. Backward compatibility and migration rules are a post-v1.0 concern — the schema will change significantly before stabilizing.

## Candidate finding schema

This is the output format for `fresh-eyes-review` and `challenger-review`. The `finding-synthesizer` consumes arrays of these from all review sources.

```json
{
  "finding_id": str,
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
