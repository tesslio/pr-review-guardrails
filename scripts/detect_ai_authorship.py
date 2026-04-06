#!/usr/bin/env python3
"""
Determine whether a PR was AI-assisted by inspecting commit metadata.

Detection is metadata-based, not heuristic. If the commit says it was
AI-assisted, we believe it. If it doesn't, we don't guess.

False negatives are fine. False positives are not.
"""

import json
import re
import subprocess
import sys
import os


# Known AI co-author patterns (case-insensitive matching)
AI_PATTERNS = [
    (r"claude", "claude"),
    (r"anthropic", "claude"),
    (r"copilot", "copilot"),
    (r"github copilot", "copilot"),
    (r"cursor", "cursor"),
    (r"codeium", "codeium"),
    (r"tabnine", "tabnine"),
    (r"cody", "cody"),
    (r"sourcegraph", "cody"),
    (r"windsurf", "windsurf"),
    (r"aider", "aider"),
]


def run_cmd(cmd, timeout=30):
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", 1


def detect(repo_root, base_branch="origin/main"):
    """Parse Co-Authored-By trailers from all commits in the PR branch."""
    stdout, rc = run_cmd(
        f"git -C {repo_root} log --format='%(trailers:key=Co-Authored-By)' "
        f"{base_branch}..HEAD"
    )

    if rc != 0:
        return {"ai_assisted": False, "ai_tools": [], "ai_commit_ratio": 0.0}

    # Count total commits
    commit_count_str, _ = run_cmd(
        f"git -C {repo_root} rev-list --count {base_branch}..HEAD"
    )
    total_commits = int(commit_count_str) if commit_count_str.isdigit() else 0

    if total_commits == 0:
        return {"ai_assisted": False, "ai_tools": [], "ai_commit_ratio": 0.0}

    # Parse trailers
    ai_tools_found = set()
    ai_commit_count = 0
    current_commit_has_ai = False

    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            if current_commit_has_ai:
                ai_commit_count += 1
                current_commit_has_ai = False
            continue

        # Check against known patterns
        for pattern, tool_name in AI_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                ai_tools_found.add(tool_name)
                current_commit_has_ai = True
                break

    # Handle last commit
    if current_commit_has_ai:
        ai_commit_count += 1

    ai_tools = sorted(ai_tools_found)
    ai_commit_ratio = ai_commit_count / total_commits if total_commits > 0 else 0.0

    return {
        "ai_assisted": len(ai_tools) > 0,
        "ai_tools": ai_tools,
        "ai_commit_ratio": round(ai_commit_ratio, 3),
        "total_commits": total_commits,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Detect AI authorship from commit trailers")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--base-branch", default="origin/main", help="Base branch")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    result = detect(os.path.abspath(args.repo_root), args.base_branch)

    if args.format == "json":
        print(json.dumps(result))
    else:
        if result["ai_assisted"]:
            tools = ", ".join(result["ai_tools"])
            ratio = f"{result['ai_commit_ratio']:.0%}"
            print(f"AI-assisted: yes (tools: {tools}, {ratio} of commits)")
        else:
            print("AI-assisted: no")


if __name__ == "__main__":
    main()
