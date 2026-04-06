#!/usr/bin/env python3
"""
Assign risk lane and contributing factors.

This is the routing decision that determines which skills run. If it gets a
classification wrong, the whole workflow degrades silently. Treat this as the
most important script in the tile.

When confidence is low, round UP. A false red costs one extra review pass.
A false green can miss a real issue.
"""

import json
import re
import sys
import os
from pathlib import Path


# Red factors — any one of these forces red lane
RED_FACTOR_PATTERNS = {
    "auth-sensitive": [
        r"auth/", r"permissions?/", r"acl/", r"rbac/",
        r"trust.?bound", r"security/", r"oauth", r"saml",
        r"session", r"token", r"jwt",
    ],
    "migration": [
        r"db/migrate", r"migrations?/", r"alembic/", r"flyway/",
        r"schema\.(?:sql|rb|py)", r"\.sql$",
    ],
    "public-api": [
        r"openapi", r"swagger", r"\.proto$", r"graphql/schema",
        r"routes\.", r"endpoints?\.", r"api/v\d",
    ],
    "infra-deploy": [
        r"terraform/", r"\.tf$", r"helm/", r"k8s/", r"kubernetes/",
        r"docker", r"Dockerfile", r"\.github/workflows/",
        r"ci/", r"cd/", r"deploy",
    ],
    "secrets-trust": [
        r"secrets?/", r"\.env\.", r"credentials",
        r"crypto", r"encrypt", r"decrypt", r"signing",
        r"key\.(?:pem|pub|priv)", r"certificate",
    ],
    "concurrency": [
        r"mutex", r"lock\.", r"semaphore", r"channel\.",
        r"async\.", r"thread", r"worker_pool",
        r"race", r"atomic",
    ],
    "cache-invalidation": [
        r"cache\.(?:delete|clear|invalidat|evict|flush)",
        r"ttl", r"cache_key",
    ],
    "rollout-feature-flag": [
        r"feature.?flag", r"feature.?toggle", r"rollout",
        r"kill.?switch", r"canary", r"gradual",
    ],
}

# Moderate factors — contribute to yellow
MODERATE_FACTOR_PATTERNS = {
    "business-logic": [
        r"service/", r"domain/", r"model/", r"handler/",
        r"controller/", r"usecase/",
    ],
    "config-change": [
        r"config/", r"settings\.", r"\.ya?ml$", r"\.toml$",
        r"\.ini$", r"\.conf$",
    ],
}

# Green-only patterns — if ALL files match these, it's green regardless
GREEN_ONLY_PATTERNS = [
    r"\.md$", r"README", r"CHANGELOG", r"LICENSE",
    r"docs?/", r"documentation/",
    r"test_", r"_test\.", r"\.test\.", r"\.spec\.",
    r"__tests__/", r"tests?/",
    r"\.gitignore$", r"\.editorconfig$",
]


def matches_any(path, patterns):
    """Check if a file path matches any of the given regex patterns."""
    return any(re.search(p, path, re.IGNORECASE) for p in patterns)


def is_green_only(path):
    """Check if a file is docs/tests/formatting only."""
    return matches_any(path, GREEN_ONLY_PATTERNS)


def classify(touched_files, diff_stats, subsystems, repo_root="."):
    """
    Classify risk lane based on touched files and context.

    Returns:
        dict with lane, factors, confidence, and override info.
    """
    factors = []
    has_red = False
    moderate_count = 0

    file_paths = [f["path"] for f in touched_files]

    # Check if ALL files are green-only
    if all(is_green_only(p) for p in file_paths) and file_paths:
        return {
            "lane": "green",
            "confidence": "high",
            "factors": [],
            "override_applied": False,
            "override_source": None,
        }

    # Check red factors
    for factor_name, patterns in RED_FACTOR_PATTERNS.items():
        matching_files = [p for p in file_paths if matches_any(p, patterns)]
        if matching_files:
            factors.append({
                "factor": factor_name,
                "files": matching_files,
                "severity": "red",
            })
            has_red = True

    # Check multi-subsystem (red factor)
    if len(subsystems) > 2:
        factors.append({
            "factor": "multi-subsystem",
            "files": file_paths,
            "severity": "red",
        })
        has_red = True

    # Check moderate factors
    for factor_name, patterns in MODERATE_FACTOR_PATTERNS.items():
        matching_files = [p for p in file_paths if matches_any(p, patterns)]
        if matching_files:
            factors.append({
                "factor": factor_name,
                "files": matching_files,
                "severity": "moderate",
            })
            moderate_count += 1

    # Large diff is a moderate factor
    total_changes = diff_stats.get("insertions", 0) + diff_stats.get("deletions", 0)
    if total_changes > 500:
        factors.append({
            "factor": "large-diff",
            "files": file_paths,
            "severity": "moderate",
        })
        moderate_count += 1

    # Determine lane
    if has_red:
        lane = "red"
    elif moderate_count >= 1:
        lane = "yellow"
    else:
        lane = "green"

    # Determine confidence
    if has_red or (moderate_count == 0 and not factors):
        confidence = "high"
    elif moderate_count <= 2:
        confidence = "medium"
    else:
        confidence = "low"

    # Apply repo-specific risk overrides
    override_applied = False
    override_source = None
    risk_overrides_path = Path(repo_root) / ".pr-review" / "risk-overrides.json"
    if risk_overrides_path.exists():
        try:
            with open(risk_overrides_path) as f:
                overrides = json.load(f)
            for override in overrides:
                pattern = override.get("pattern", "")
                override_lane = override.get("lane", "")
                for p in file_paths:
                    if re.search(pattern, p, re.IGNORECASE):
                        # Overrides can only escalate, never downgrade
                        lane_order = {"green": 0, "yellow": 1, "red": 2}
                        if lane_order.get(override_lane, 0) > lane_order.get(lane, 0):
                            lane = override_lane
                            override_applied = True
                            override_source = f"risk-overrides.json: {pattern}"
                            factors.append({
                                "factor": f"override: {pattern}",
                                "files": [p],
                                "severity": "red" if override_lane == "red" else "moderate",
                            })
        except (json.JSONDecodeError, KeyError):
            pass

    # Check PR description for manual risk override (escalate only)
    # This is handled by the caller passing PR description

    # When confidence is low, round UP
    if confidence == "low":
        lane_escalation = {"green": "yellow", "yellow": "red", "red": "red"}
        lane = lane_escalation[lane]

    return {
        "lane": lane,
        "confidence": confidence,
        "factors": factors,
        "override_applied": override_applied,
        "override_source": override_source,
    }


def check_pr_description_override(pr_description, current_lane):
    """Check for explicit risk override in PR description. Escalate only."""
    if not pr_description:
        return current_lane, False

    match = re.search(r"risk:\s*(red|yellow)", pr_description, re.IGNORECASE)
    if match:
        requested_lane = match.group(1).lower()
        lane_order = {"green": 0, "yellow": 1, "red": 2}
        if lane_order.get(requested_lane, 0) > lane_order.get(current_lane, 0):
            return requested_lane, True

    return current_lane, False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Classify change risk")
    parser.add_argument("--context", required=True, help="Path to PR context JSON")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--output", default="-", help="Output file (- for stdout)")
    args = parser.parse_args()

    with open(args.context) as f:
        context = json.load(f)

    touched_files = context.get("touched_files", [])
    diff_stats = context.get("diff_stats", {})
    subsystems = context.get("subsystems", [])

    result = classify(touched_files, diff_stats, subsystems, args.repo_root)

    # Check PR description override
    pr_desc = context.get("pr", {}).get("description", "")
    new_lane, overridden = check_pr_description_override(pr_desc, result["lane"])
    if overridden:
        result["lane"] = new_lane
        result["override_applied"] = True
        result["override_source"] = "PR description"

    output = json.dumps(result, indent=2)
    if args.output == "-":
        print(output)
    else:
        with open(args.output, "w") as f:
            f.write(output)


if __name__ == "__main__":
    main()
