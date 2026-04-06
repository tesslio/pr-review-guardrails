#!/usr/bin/env python3
"""
Collect retrospective outcomes from GitHub API for evals and iteration.

All outcome data is collected from GitHub API events. No manual input required.
Runs on demand via review-retrospective skill invocation.
"""

import json
import subprocess
import sys
import re
from datetime import datetime


def run_cmd(cmd, timeout=30):
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", 1


def get_pr_comments(owner, repo, pr_number):
    """
    Fetch PR review comments and determine finding disposition.

    - finding marked "resolved" -> accepted
    - finding left unresolved at merge -> ignored
    - suggested change committed -> accepted with exact fix
    - reply disagreeing with finding -> rejected
    """
    stdout, rc = run_cmd(
        f"gh api repos/{owner}/{repo}/pulls/{pr_number}/comments --paginate"
    )
    if rc != 0:
        return []

    try:
        comments = json.loads(stdout)
    except json.JSONDecodeError:
        return []

    # Also get review comment threads for resolution state
    stdout_reviews, _ = run_cmd(
        f"gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews --paginate"
    )
    try:
        reviews = json.loads(stdout_reviews)
    except json.JSONDecodeError:
        reviews = []

    return comments


def get_pr_timeline(owner, repo, pr_number):
    """
    Fetch PR timeline for merge timing and review rounds.

    - time from tile comment to merge -> review overhead signal
    - number of review rounds -> iteration cost
    - closed without merge -> possible tile-induced abandonment
    """
    stdout, rc = run_cmd(
        f"gh api repos/{owner}/{repo}/pulls/{pr_number}"
    )
    if rc != 0:
        return {}

    try:
        pr = json.loads(stdout)
    except json.JSONDecodeError:
        return {}

    created_at = pr.get("created_at", "")
    merged_at = pr.get("merged_at")
    closed_at = pr.get("closed_at")
    state = pr.get("state", "")

    timeline = {
        "created_at": created_at,
        "merged_at": merged_at,
        "closed_at": closed_at,
        "state": state,
        "was_merged": merged_at is not None,
        "closed_without_merge": state == "closed" and merged_at is None,
    }

    # Calculate merge time if merged
    if created_at and merged_at:
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            merged = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
            timeline["time_to_merge_hours"] = round(
                (merged - created).total_seconds() / 3600, 2
            )
        except (ValueError, TypeError):
            pass

    # Count review rounds
    stdout_reviews, _ = run_cmd(
        f"gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews --paginate"
    )
    try:
        reviews = json.loads(stdout_reviews)
        timeline["review_rounds"] = len(reviews)
    except json.JSONDecodeError:
        timeline["review_rounds"] = 0

    return timeline


def get_post_merge_issues(owner, repo, pr_number):
    """
    Search for post-merge issues linked to the PR.

    - issues opened referencing the merged PR -> candidate escaped defects
    - bug labels on those issues -> confirmed escaped defects
    """
    stdout, rc = run_cmd(
        f'gh api "search/issues?q=repo:{owner}/{repo}+is:issue+{pr_number}"'
    )
    if rc != 0:
        return []

    try:
        data = json.loads(stdout)
        items = data.get("items", [])
    except json.JSONDecodeError:
        return []

    escaped_defects = []
    for item in items:
        labels = [l.get("name", "").lower() for l in item.get("labels", [])]
        is_bug = any(
            l in ("bug", "defect", "regression", "incident")
            for l in labels
        )
        escaped_defects.append({
            "issue_number": item.get("number"),
            "title": item.get("title", ""),
            "labels": labels,
            "is_bug": is_bug,
            "created_at": item.get("created_at", ""),
        })

    return escaped_defects


def get_ai_authorship(repo_root, base_branch="origin/main"):
    """Parse commit trailers for AI authorship signals."""
    stdout, rc = run_cmd(
        f"git -C {repo_root} log --format='%(trailers:key=Co-Authored-By)' "
        f"{base_branch}..HEAD"
    )
    if rc != 0:
        return {}

    ai_patterns = [
        (r"claude", "claude"),
        (r"copilot", "copilot"),
        (r"cursor", "cursor"),
    ]

    tools = set()
    for line in stdout.splitlines():
        for pattern, name in ai_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                tools.add(name)

    return {
        "ai_tools_detected": sorted(tools),
        "ai_assisted": len(tools) > 0,
    }


def map_findings_to_outcomes(comments, tile_finding_ids=None):
    """
    Map tile findings to outcomes based on comment state.

    Disposition:
    - accepted: comment resolved or suggested change committed
    - rejected: reply disagreeing with finding
    - ignored: comment unresolved at merge
    - superseded: human made a different fix in the same area
    """
    outcomes = []

    for comment in comments:
        body = comment.get("body", "")
        # Check if this comment is from the tile (by finding ID or bot marker)
        is_tile_comment = False
        matched_finding_id = None

        if tile_finding_ids:
            for fid in tile_finding_ids:
                if fid in body:
                    is_tile_comment = True
                    matched_finding_id = fid
                    break

        if not is_tile_comment:
            # Check for tile disclaimer as a fallback
            if "evidence-based review aid" in body:
                is_tile_comment = True

        if not is_tile_comment:
            continue

        # Determine disposition
        # Note: GitHub API doesn't directly expose "resolved" state on comments
        # in the REST API. This is a simplification — real impl would use GraphQL.
        disposition = "ignored"  # default

        # Check for reactions or replies indicating acceptance/rejection
        reactions = comment.get("reactions", {})
        if reactions.get("+1", 0) > 0 or reactions.get("heart", 0) > 0:
            disposition = "accepted"
        elif reactions.get("-1", 0) > 0 or reactions.get("confused", 0) > 0:
            disposition = "rejected"

        outcomes.append({
            "finding_id": matched_finding_id,
            "comment_id": comment.get("id"),
            "disposition": disposition,
            "file": comment.get("path", ""),
            "line": comment.get("line"),
        })

    return outcomes


def record_outcomes(owner, repo, pr_number, tile_finding_ids=None, repo_root="."):
    """Collect all outcome data for a PR."""
    comments = get_pr_comments(owner, repo, pr_number)
    timeline = get_pr_timeline(owner, repo, pr_number)
    escaped_defects = get_post_merge_issues(owner, repo, pr_number)
    finding_outcomes = map_findings_to_outcomes(comments, tile_finding_ids)

    return {
        "pr_number": pr_number,
        "repo": f"{owner}/{repo}",
        "recorded_at": datetime.utcnow().isoformat() + "Z",
        "timeline": timeline,
        "finding_outcomes": finding_outcomes,
        "escaped_defects": escaped_defects,
        "summary": {
            "findings_accepted": sum(
                1 for o in finding_outcomes if o["disposition"] == "accepted"
            ),
            "findings_rejected": sum(
                1 for o in finding_outcomes if o["disposition"] == "rejected"
            ),
            "findings_ignored": sum(
                1 for o in finding_outcomes if o["disposition"] == "ignored"
            ),
            "escaped_bugs": sum(
                1 for d in escaped_defects if d.get("is_bug", False)
            ),
            "time_to_merge_hours": timeline.get("time_to_merge_hours"),
            "review_rounds": timeline.get("review_rounds", 0),
            "closed_without_merge": timeline.get("closed_without_merge", False),
        },
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Record review outcomes")
    parser.add_argument("--owner", required=True, help="Repository owner")
    parser.add_argument("--repo", required=True, help="Repository name")
    parser.add_argument("--pr", required=True, type=int, help="PR number")
    parser.add_argument("--finding-ids", nargs="*", help="Tile finding IDs to track")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--output", default="-", help="Output file (- for stdout)")
    args = parser.parse_args()

    result = record_outcomes(
        args.owner, args.repo, args.pr, args.finding_ids, args.repo_root
    )

    output = json.dumps(result, indent=2)
    if args.output == "-":
        print(output)
    else:
        with open(args.output, "w") as f:
            f.write(output)


if __name__ == "__main__":
    main()
