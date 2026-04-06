#!/usr/bin/env python3
"""
Mark likely attention zones in the diff.

Hotspots are areas where reviewers should spend disproportionate attention —
not findings themselves, but focus magnets.
"""

import json
import re
import sys


# Hotspot detection patterns: category -> list of (regex, explanation)
HOTSPOT_PATTERNS = {
    "permission-authorization": [
        (r"\bcan_\w+", "permission check"),
        (r"\bis_authorized\b", "authorization check"),
        (r"\bhas_permission\b", "permission check"),
        (r"\brole_check\b|\bcheck_role\b", "role validation"),
        (r"\bacl\b", "ACL logic"),
        (r"\brbac\b", "RBAC logic"),
        (r"@require_auth|@login_required|@authenticated", "auth decorator"),
        (r"requiredRoles?\b|allowedRoles?\b|roles?\.(every|some|includes)", "role array check — verify call-site semantics"),
        (r"@require_role|require_role|check_role|has_role", "role requirement"),
    ],
    "serialization-boundary": [
        (r"json\.(dumps?|loads?|encode|decode)", "JSON serialization"),
        (r"\.to_json\b|\.from_json\b", "JSON conversion"),
        (r"\.to_dict\b|\.from_dict\b", "dict serialization"),
        (r"protobuf|\.proto\b", "protobuf serialization"),
        (r"serialize|deserialize|marshal|unmarshal", "serialization boundary"),
        (r"request\.body|response\.json|req\.body", "API request/response shaping"),
    ],
    "null-error-handling": [
        (r"\bcatch\s*\(|\bexcept\s", "exception handler"),
        (r"if\s+\w+\s*(==|!=|is)\s*nil\b", "nil check"),
        (r"if\s+\w+\s*(==|!=|is)\s*None\b", "None check"),
        (r"\?\?|Optional<|\.unwrap\(\)|\?\.|\!\.", "optional/null handling"),
        (r"if\s+err\s*!=\s*nil", "Go error check"),
        (r"\.catch\(|\.then\(", "promise error handling"),
        (r"Result<|Err\(|Ok\(", "Rust result handling"),
    ],
    "retry-timeout": [
        (r"retry|retries|max_retries|retry_count", "retry logic"),
        (r"backoff|exponential_backoff", "backoff strategy"),
        (r"timeout|deadline|time_limit", "timeout configuration"),
        (r"context\.WithTimeout|context\.WithDeadline", "Go deadline propagation"),
    ],
    "cache-invalidation": [
        (r"cache\.(delete|clear|invalidat|evict|flush|remove)", "cache invalidation"),
        (r"\.ttl\b|\.expire\b|\.set_expiry\b", "TTL change"),
        (r"cache_key|cache\.get|cache\.set", "cache key construction"),
        (r"redis\.(del|flushdb|expire)", "Redis cache operation"),
    ],
    "feature-flag": [
        (r"feature_flag|feature_toggle|is_enabled|is_feature", "feature flag check"),
        (r"rollout_percent|rollout_ratio", "rollout percentage"),
        (r"flag_value|get_flag|check_flag", "flag evaluation"),
        (r"kill_switch|circuit_breaker", "kill switch / circuit breaker"),
    ],
    "data-migration": [
        (r"ALTER\s+TABLE|ADD\s+COLUMN|DROP\s+COLUMN", "schema change"),
        (r"CREATE\s+(TABLE|INDEX)", "new schema object"),
        (r"backfill|data_migration|migrate_data", "data migration logic"),
        (r"\.execute\(.*(?:ALTER|CREATE|DROP)", "DDL execution"),
    ],
    "sql-query-construction": [
        (r"f['\"].*(?:SELECT|INSERT|UPDATE|DELETE)", "string-interpolated SQL"),
        (r"\.format\(.*(?:SELECT|INSERT|UPDATE|DELETE)", "format-string SQL"),
        (r"\+.*(?:SELECT|INSERT|UPDATE|DELETE)", "concatenated SQL"),
        (r"raw_sql|raw\(|execute\(", "raw SQL execution"),
    ],
    "crypto-operation": [
        (r"hashlib|sha256|sha512|md5|bcrypt", "hashing operation"),
        (r"\.sign\(|\.verify\(|signature", "signing/verification"),
        (r"generate_key|private_key|public_key", "key management"),
        (r"encrypt|decrypt|cipher|aes|rsa", "encryption operation"),
        (r"token_gen|generate_token|jwt\.encode", "token generation"),
    ],
    "external-service": [
        (r"requests\.(get|post|put|delete|patch)", "HTTP client call"),
        (r"http\.client|fetch\(|axios\.", "HTTP request"),
        (r"\.publish\(|\.send_message\(|\.enqueue\(", "queue/message producer"),
        (r"\.consume\(|\.subscribe\(|\.on_message\(", "queue/message consumer"),
        (r"boto3|s3_client|dynamodb|sqs", "AWS SDK call"),
        (r"grpc\.|\.Dial\(|\.NewClient\(", "gRPC call"),
    ],
    "output-encoding": [
        (r"\.csv|csv\.|to_csv|write_csv|CSVWriter|csv\.writer", "CSV generation"),
        (r"text/csv|application/csv|\.xlsx|spreadsheet", "spreadsheet output"),
        (r"Content-Disposition.*attachment", "file download"),
        (r"\.writerow\(|\.writerows\(|DictWriter", "CSV row writing"),
        (r"export.*csv|download.*csv|generate.*report", "CSV export"),
        (r"\.createObjectURL|Blob\(", "client-side file generation"),
    ],
    "shared-resource-contention": [
        (r"pool\.Get|pool\.Acquire|getConnection|connectionPool", "connection pool acquisition"),
        (r"health.*check|healthz|readyz|livez|/health", "health check endpoint"),
        (r"\.ping\(|SELECT\s+1|SELECT\s+NOW", "health probe query"),
        (r"worker|gunicorn|uwsgi|cluster\.fork|PM2", "multi-process worker"),
        (r"in_memory|seen_ids|dedup_set|processed_set", "in-memory cross-request state"),
        (r"sync\.Map|sync\.Mutex|threading\.Lock", "shared-memory synchronization"),
    ],
    "infrastructure-lifecycle": [
        (r"lifecycle_rule|lifecycle_configuration|transition", "storage lifecycle transition"),
        (r"storage_class|GLACIER|DEEP_ARCHIVE|INTELLIGENT_TIERING", "storage tier change"),
        (r"backup_retention|backup_window|delete_automated_backups", "backup retention policy"),
        (r"availability_zone|multi_az|replicate_source", "availability/replication config"),
        (r"retention_period|retention_in_days|log_retention", "data retention policy"),
        (r"snapshot_identifier|final_snapshot|skip_final_snapshot", "snapshot configuration"),
    ],
}


def parse_diff_hunks(raw_diff):
    """Parse a unified diff into per-file hunks with line numbers."""
    files = []
    current_file = None
    current_hunk_start = None
    current_line = 0

    for line in raw_diff.splitlines():
        # New file
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue
        if line.startswith("--- "):
            continue

        # Hunk header
        hunk_match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if hunk_match:
            current_line = int(hunk_match.group(1)) - 1
            continue

        # Added/modified lines (the ones we care about for hotspot detection)
        if line.startswith("+") and not line.startswith("+++"):
            current_line += 1
            if current_file:
                files.append({
                    "file": current_file,
                    "line": current_line,
                    "content": line[1:],  # Strip the + prefix
                })
        elif line.startswith("-"):
            # Deleted lines don't advance the line counter
            continue
        else:
            current_line += 1

    return files


def detect_hotspots(diff_lines, risk_factors=None):
    """Detect hotspots by pattern-matching against diff lines."""
    risk_files = set()
    if risk_factors:
        for factor in risk_factors:
            risk_files.update(factor.get("files", []))

    hotspots = []
    # Group consecutive matches in the same file/category
    seen = {}  # (file, category) -> hotspot

    for dl in diff_lines:
        for category, patterns in HOTSPOT_PATTERNS.items():
            for pattern, explanation in patterns:
                if re.search(pattern, dl["content"], re.IGNORECASE):
                    key = (dl["file"], category)
                    if key in seen:
                        # Extend the existing hotspot range
                        seen[key]["line_end"] = dl["line"]
                    else:
                        is_risk = dl["file"] in risk_files
                        hotspot = {
                            "file": dl["file"],
                            "line_start": dl["line"],
                            "line_end": dl["line"],
                            "category": category,
                            "why": explanation,
                            "risk_contributing": is_risk,
                        }
                        seen[key] = hotspot
                        hotspots.append(hotspot)
                    break  # One match per category per line is enough
            # Don't break outer loop — a line can match multiple categories

    return hotspots


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Map diff hotspots")
    parser.add_argument("--context", required=True, help="Path to PR context JSON")
    parser.add_argument("--risk", help="Path to risk classification JSON")
    parser.add_argument("--output", default="-", help="Output file (- for stdout)")
    args = parser.parse_args()

    with open(args.context) as f:
        context = json.load(f)

    risk_factors = []
    if args.risk:
        with open(args.risk) as f:
            risk_data = json.load(f)
            risk_factors = risk_data.get("factors", [])

    raw_diff = context.get("raw_diff", "")
    diff_lines = parse_diff_hunks(raw_diff)
    hotspots = detect_hotspots(diff_lines, risk_factors)

    output = json.dumps(hotspots, indent=2)
    if args.output == "-":
        print(output)
    else:
        with open(args.output, "w") as f:
            f.write(output)


if __name__ == "__main__":
    main()
