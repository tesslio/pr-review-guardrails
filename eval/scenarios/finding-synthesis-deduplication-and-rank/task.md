# Consolidate Overlapping Code Review Findings

## Problem/Feature Description

Your team's review pipeline ran two independent reviewers on a pull request — a primary fresh-eyes reviewer and a challenger reviewer — and both produced their own sets of findings. Before handing the review off to a human, you need to consolidate these findings into a clean, prioritized list. The two reviewers sometimes flagged the same issue in different words, sometimes agreed on an issue (corroborating it), and sometimes disagreed (one flagged something the other found safe). The raw output also contains some findings that are probably not worth a human's attention.

Your task is to merge, deduplicate, rank, and suppress findings from both reviewers and from a verifier, producing a final consolidated set that is ready for human review. The human reviewer has limited time and will not want to see duplicates, vague style observations, or findings that amount to speculation.

## Output Specification

Produce two files:

1. `merged_findings.json` — the synthesized output containing ALL findings (both surfaced and suppressed). Each finding must include all original fields from the input, plus metadata fields that capture the synthesis result for each finding — including whether findings from different reviewers agreed or disagreed, the overall confidence after merging, and whether the finding was suppressed and why.

2. `synthesis_report.md` — a brief (200–300 word) explanation of:
   - How many findings were received from each source
   - How you handled overlapping findings across the three sources, including any conflicts where reviewers disagreed
   - How many findings were suppressed and why
   - The final ranking order and the score for each surfaced finding

## Input Files

The following files are provided as inputs. Extract them before beginning.

=============== FILE: inputs/fresh_eyes_findings.json ===============
[
  {
    "finding_id": "fe-001",
    "source": "fresh_eyes",
    "file": "src/cache/redis_client.py",
    "line_start": 34,
    "line_end": 36,
    "issue": "Cache key uses unsanitized user input — potential for cache poisoning",
    "severity": 3,
    "confidence": 3,
    "evidence": "User-supplied session_id concatenated directly into cache key at line 35 with no normalization.",
    "verification_support": 2
  },
  {
    "finding_id": "fe-002",
    "source": "fresh_eyes",
    "file": "src/cache/redis_client.py",
    "line_start": 34,
    "line_end": 36,
    "issue": "Redis key construction allows arbitrary user-controlled strings as cache keys",
    "severity": 3,
    "confidence": 3,
    "evidence": "Line 35: key = f'session:{session_id}' where session_id is from request.",
    "verification_support": 2
  },
  {
    "finding_id": "fe-003",
    "source": "fresh_eyes",
    "file": "src/api/handler.py",
    "line_start": 88,
    "line_end": 92,
    "issue": "Error response includes full exception stack trace",
    "severity": 2,
    "confidence": 3,
    "evidence": "Line 90: return jsonify({'error': str(e), 'trace': traceback.format_exc()})",
    "verification_support": 1
  },
  {
    "finding_id": "fe-004",
    "source": "fresh_eyes",
    "file": "src/api/handler.py",
    "line_start": 15,
    "line_end": 15,
    "issue": "Variable name 'x' is not descriptive",
    "severity": 1,
    "confidence": 3,
    "evidence": "Naming convention violation.",
    "verification_support": 1
  }
]

=============== FILE: inputs/challenger_findings.json ===============
[
  {
    "finding_id": "ch-001",
    "source": "challenger",
    "file": "src/cache/redis_client.py",
    "line_start": 34,
    "line_end": 36,
    "issue": "Cache key injection via session_id parameter — allows overwriting other users' cache entries",
    "severity": 3,
    "confidence": 3,
    "evidence": "An attacker who controls session_id can supply '../other_user_key' to read or overwrite arbitrary cache entries.",
    "verification_support": 2,
    "classification": "confirms"
  },
  {
    "finding_id": "ch-002",
    "source": "challenger",
    "file": "src/api/handler.py",
    "line_start": 88,
    "line_end": 92,
    "issue": "Stack traces in error responses are safe in this context — internal API only",
    "severity": 1,
    "confidence": 2,
    "evidence": "Router config at src/api/routes.py:12 restricts this handler to internal VPC subnet; external callers never reach it.",
    "verification_support": 1,
    "classification": "refutes"
  },
  {
    "finding_id": "ch-003",
    "source": "challenger",
    "file": "src/cache/redis_client.py",
    "line_start": 51,
    "line_end": 55,
    "issue": "Cache TTL set to 0 for anonymous sessions — entries never expire",
    "severity": 2,
    "confidence": 3,
    "evidence": "Line 53: ttl = user.ttl if user.authenticated else 0. A TTL of 0 in Redis means the key never expires.",
    "verification_support": 1,
    "classification": "novel"
  }
]

=============== FILE: inputs/verifier_findings.json ===============
[
  {
    "finding_id": "v-001",
    "source": "verifier",
    "verifier_name": "bandit",
    "file": "src/api/handler.py",
    "line_start": 90,
    "line_end": 90,
    "issue": "B104: Possible binding to all interfaces",
    "severity": 1,
    "confidence": 2,
    "evidence": "bandit B104 hit on line 90",
    "verification_support": 3
  }
]
