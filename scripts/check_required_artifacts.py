#!/usr/bin/env python3
"""
Flag missing review-support artifacts.

What's required depends on the risk lane — green-lane changes need almost
nothing, red-lane changes need everything.
"""

import json
import re
import sys
import os
from pathlib import Path


# Default artifact requirements by lane
DEFAULT_REQUIREMENTS = {
    "green": [
        {
            "artifact": "PR description or linked issue",
            "check": "has_intent",
            "required": False,
            "why_required": "Recommended: helps reviewers understand why the change was made",
        },
    ],
    "yellow": [
        {
            "artifact": "PR description or linked issue",
            "check": "has_intent",
            "required": True,
            "why_required": "Required: reviewers need to understand the motivation for business logic changes",
        },
        {
            "artifact": "Tests covering changed behavior",
            "check": "has_tests",
            "required": True,  # required if test files exist for the area
            "why_required": "Required: changed behavior must be verified by tests",
        },
        {
            "artifact": "Changelog entry",
            "check": "has_changelog",
            "required": False,  # only if repo has changelog convention
            "why_required": "Required if repo has a changelog convention",
        },
    ],
    "red": [
        {
            "artifact": "PR description or linked issue",
            "check": "has_intent",
            "required": True,
            "why_required": "Required: high-risk changes must have clear intent documentation",
        },
        {
            "artifact": "Tests covering changed behavior",
            "check": "has_tests",
            "required": True,
            "why_required": "Required: high-risk changes must have test coverage",
        },
        {
            "artifact": "Migration/rollback guidance",
            "check": "has_migration_guidance",
            "required": True,  # only for migration changes
            "why_required": "Required for migration changes: rollback plan must be documented",
        },
        {
            "artifact": "Rollout note",
            "check": "has_rollout_note",
            "required": True,  # only for rollout-sensitive changes
            "why_required": "Required for rollout-sensitive changes: deployment strategy must be documented",
        },
        {
            "artifact": "Security review note",
            "check": "has_security_note",
            "required": True,  # only for auth/secrets/trust-boundary
            "why_required": "Required for auth/security changes: security implications must be documented",
        },
    ],
}


def check_has_intent(context, risk):
    """Check if PR has description or linked issue explaining why."""
    pr = context.get("pr", {})
    description = pr.get("description", "") or ""
    linked_issues = context.get("linked_issues", [])

    # Has meaningful description (more than just a title repeat)
    if len(description.strip()) > 20:
        return True
    # Has linked issues
    if linked_issues:
        return True
    return False


def check_has_tests(context, risk):
    """Check if changed behavior has test coverage."""
    related_tests = context.get("related_tests", [])
    if not related_tests:
        return True  # No source files that need tests

    # Check if test files exist for changed source files
    missing_tests = [t for t in related_tests if not t.get("test_exists", False)]
    if not missing_tests:
        return True

    # If some tests are missing but area has no test convention, it's ok for yellow
    return False


def check_has_changelog(context, risk, repo_root="."):
    """Check for changelog entry if repo has a changelog convention."""
    changelog_files = ["CHANGELOG.md", "CHANGELOG", "CHANGES.md", "HISTORY.md"]
    has_changelog_convention = any(
        (Path(repo_root) / f).exists() for f in changelog_files
    )
    if not has_changelog_convention:
        return True  # No convention, not required

    # Check if any changelog file was touched
    touched_paths = [f["path"] for f in context.get("touched_files", [])]
    return any(
        any(cf.lower() in tp.lower() for cf in changelog_files)
        for tp in touched_paths
    )


def check_has_migration_guidance(context, risk):
    """Check for migration/rollback guidance in PR description."""
    # Only required if migration factors are present
    factors = risk.get("factors", [])
    has_migration_factor = any(
        "migration" in f.get("factor", "").lower() for f in factors
    )
    if not has_migration_factor:
        return True

    description = context.get("pr", {}).get("description", "") or ""
    migration_keywords = [
        r"rollback", r"migration plan", r"backward.?compat",
        r"revert", r"down migration", r"schema change",
    ]
    return any(re.search(kw, description, re.IGNORECASE) for kw in migration_keywords)


def check_has_rollout_note(context, risk):
    """Check for rollout note in PR description."""
    factors = risk.get("factors", [])
    has_rollout_factor = any(
        "rollout" in f.get("factor", "").lower() or
        "feature" in f.get("factor", "").lower()
        for f in factors
    )
    if not has_rollout_factor:
        return True

    description = context.get("pr", {}).get("description", "") or ""
    rollout_keywords = [
        r"rollout", r"deploy", r"feature flag", r"gradual",
        r"canary", r"percentage", r"kill switch",
    ]
    return any(re.search(kw, description, re.IGNORECASE) for kw in rollout_keywords)


def check_has_security_note(context, risk):
    """Check for security review note in PR description."""
    factors = risk.get("factors", [])
    has_security_factor = any(
        f.get("factor", "") in ("auth-sensitive", "secrets-trust")
        for f in factors
    )
    if not has_security_factor:
        return True

    description = context.get("pr", {}).get("description", "") or ""
    security_keywords = [
        r"security", r"auth", r"permission", r"trust",
        r"credential", r"secret", r"vulnerability",
        r"threat model", r"attack surface",
    ]
    return any(re.search(kw, description, re.IGNORECASE) for kw in security_keywords)


CHECK_FUNCTIONS = {
    "has_intent": check_has_intent,
    "has_tests": check_has_tests,
    "has_changelog": check_has_changelog,
    "has_migration_guidance": check_has_migration_guidance,
    "has_rollout_note": check_has_rollout_note,
    "has_security_note": check_has_security_note,
}

# Suggested locations for missing artifacts
SUGGESTED_LOCATIONS = {
    "PR description or linked issue": "PR description body",
    "Tests covering changed behavior": "test file adjacent to changed source",
    "Changelog entry": "CHANGELOG.md",
    "Migration/rollback guidance": "PR description under '## Migration' heading",
    "Rollout note": "PR description under '## Rollout' heading",
    "Security review note": "PR description under '## Security' heading",
}


def check_artifacts(context, risk, repo_root="."):
    """Check for missing artifacts based on risk lane."""
    lane = risk.get("lane", "green")
    requirements = DEFAULT_REQUIREMENTS.get(lane, [])

    # Load repo-specific overrides
    custom_config = Path(repo_root) / ".pr-review" / "required-artifacts.json"
    if custom_config.exists():
        try:
            with open(custom_config) as f:
                custom = json.load(f)
            if lane in custom:
                requirements = custom[lane]
        except (json.JSONDecodeError, KeyError):
            pass

    missing = []
    for req in requirements:
        check_name = req.get("check", "")
        check_fn = CHECK_FUNCTIONS.get(check_name)
        if not check_fn:
            continue

        # Pass extra args for checks that need them
        if check_name == "has_changelog":
            passed = check_fn(context, risk, repo_root)
        elif check_name in ("has_migration_guidance", "has_rollout_note", "has_security_note"):
            passed = check_fn(context, risk)
        else:
            passed = check_fn(context, risk)

        if not passed:
            missing.append({
                "artifact": req["artifact"],
                "why_required": req["why_required"],
                "suggested_location": SUGGESTED_LOCATIONS.get(
                    req["artifact"], "PR description"
                ),
                "required": req.get("required", False),
            })

    return missing


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Check required artifacts")
    parser.add_argument("--context", required=True, help="Path to PR context JSON")
    parser.add_argument("--risk", required=True, help="Path to risk classification JSON")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--output", default="-", help="Output file (- for stdout)")
    args = parser.parse_args()

    with open(args.context) as f:
        context = json.load(f)
    with open(args.risk) as f:
        risk = json.load(f)

    missing = check_artifacts(context, risk, args.repo_root)

    output = json.dumps(missing, indent=2)
    if args.output == "-":
        print(output)
    else:
        with open(args.output, "w") as f:
            f.write(output)


if __name__ == "__main__":
    main()
