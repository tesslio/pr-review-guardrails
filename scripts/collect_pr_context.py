#!/usr/bin/env python3
"""
Collect structured PR context and write a normalized JSON artifact.
Runs in parallel with run_verifiers.sh.

Inputs:
  - PR number or branch diff (via gh api or git diff)
  - Repo root path

Output: JSON artifact matching the context portion of the evidence pack schema.
"""

import json
import subprocess
import sys
import os
import re
import time
from pathlib import Path


def run_cmd(cmd, timeout=30, retries=0, backoff_base=2):
    """Run a shell command with optional retry and backoff."""
    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            if attempt < retries:
                time.sleep(backoff_base ** (attempt + 1))
                continue
            return "", "timeout", 1
    return "", "max retries exceeded", 1


def parse_diff_stats(repo_root, base_branch="origin/main"):
    """Parse diff metadata: files changed, insertions, deletions, renames."""
    stdout, _, rc = run_cmd(
        f"git -C {repo_root} diff --numstat {base_branch}...HEAD"
    )
    if rc != 0:
        return {"files_changed": 0, "insertions": 0, "deletions": 0}, []

    touched_files = []
    total_insertions = 0
    total_deletions = 0

    for line in stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        ins = int(parts[0]) if parts[0] != "-" else 0
        dels = int(parts[1]) if parts[1] != "-" else 0
        path = parts[2]

        # Detect renames (git shows as {old => new})
        change_type = "modified"
        if "=>" in path:
            change_type = "renamed"

        total_insertions += ins
        total_deletions += dels
        touched_files.append({
            "path": path,
            "change_type": change_type,
            "insertions": ins,
            "deletions": dels,
        })

    # Detect added/deleted files
    stdout_status, _, _ = run_cmd(
        f"git -C {repo_root} diff --name-status {base_branch}...HEAD"
    )
    status_map = {}
    for line in stdout_status.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            status_code = parts[0][0]
            file_path = parts[-1]
            if status_code == "A":
                status_map[file_path] = "added"
            elif status_code == "D":
                status_map[file_path] = "deleted"
            elif status_code == "R":
                status_map[file_path] = "renamed"

    for f in touched_files:
        clean_path = f["path"].split("=>")[-1].strip().strip("}")
        if clean_path in status_map:
            f["change_type"] = status_map[clean_path]

    stats = {
        "files_changed": len(touched_files),
        "insertions": total_insertions,
        "deletions": total_deletions,
    }
    return stats, touched_files


def infer_subsystems(repo_root, touched_files):
    """
    Infer subsystem clusters using fallback chain:
    1. CODEOWNERS if present
    2. .pr-review/subsystems.json if present
    3. Top-level directory as subsystem
    4. Single subsystem fallback
    """
    subsystem_map = {}

    # Try .pr-review/subsystems.json
    subsystems_config = Path(repo_root) / ".pr-review" / "subsystems.json"
    if subsystems_config.exists():
        try:
            with open(subsystems_config) as f:
                config = json.load(f)
            # config format: {"api": ["src/api/**"], "worker": ["src/worker/**"]}
            import fnmatch
            for tf in touched_files:
                for subsystem_name, patterns in config.items():
                    for pattern in patterns:
                        if fnmatch.fnmatch(tf["path"], pattern):
                            subsystem_map[tf["path"]] = subsystem_name
                            break
                    if tf["path"] in subsystem_map:
                        break
            if subsystem_map:
                _apply_subsystems(touched_files, subsystem_map)
                return sorted(set(subsystem_map.values()))
        except (json.JSONDecodeError, KeyError):
            pass

    # Try CODEOWNERS
    codeowners_paths = [
        Path(repo_root) / "CODEOWNERS",
        Path(repo_root) / ".github" / "CODEOWNERS",
        Path(repo_root) / "docs" / "CODEOWNERS",
    ]
    for co_path in codeowners_paths:
        if co_path.exists():
            # Use CODEOWNERS path patterns as subsystem hints
            # This is a simplification — real impl would parse ownership rules
            break

    # Fallback: top-level directory as subsystem
    for tf in touched_files:
        parts = tf["path"].split("/")
        if len(parts) > 1:
            subsystem_map[tf["path"]] = parts[0]
        else:
            subsystem_map[tf["path"]] = "root"

    _apply_subsystems(touched_files, subsystem_map)
    subsystems = sorted(set(subsystem_map.values()))

    # If everything maps to one subsystem, that's fine — multi-subsystem won't trigger
    return subsystems


def _apply_subsystems(touched_files, subsystem_map):
    """Apply subsystem labels to touched files."""
    for tf in touched_files:
        tf["subsystem"] = subsystem_map.get(tf["path"], "unknown")


def find_related_tests(repo_root, touched_files):
    """Locate nearby tests for each changed source file by convention."""
    test_patterns = [
        ("test_{name}.py", "{dir}/test_{name}.py"),
        ("{name}_test.py", "{dir}/{name}_test.py"),
        ("{name}_test.go", "{dir}/{name}_test.go"),
        ("{name}.test.ts", "{dir}/{name}.test.ts"),
        ("{name}.test.tsx", "{dir}/{name}.test.tsx"),
        ("{name}.test.js", "{dir}/{name}.test.js"),
        ("{name}.spec.ts", "{dir}/{name}.spec.ts"),
        ("{name}.spec.js", "{dir}/{name}.spec.js"),
    ]

    related = []
    for tf in touched_files:
        path = Path(tf["path"])
        # Skip test files themselves
        if any(p in path.name for p in ["test_", "_test.", ".test.", ".spec."]):
            continue
        # Skip non-source files
        if path.suffix not in (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"):
            continue

        name = path.stem
        dir_path = str(path.parent)
        found_test = False

        for _, pattern in test_patterns:
            test_path = pattern.format(name=name, dir=dir_path)
            if (Path(repo_root) / test_path).exists():
                related.append({
                    "source_file": tf["path"],
                    "test_file": test_path,
                    "test_exists": True,
                })
                found_test = True
                break

        if not found_test:
            related.append({
                "source_file": tf["path"],
                "test_file": None,
                "test_exists": False,
            })

    return related


def extract_owners(repo_root, touched_files):
    """Extract likely owners from CODEOWNERS or git blame frequency."""
    owners = []
    codeowners_path = None

    for candidate in [
        Path(repo_root) / "CODEOWNERS",
        Path(repo_root) / ".github" / "CODEOWNERS",
    ]:
        if candidate.exists():
            codeowners_path = candidate
            break

    if codeowners_path:
        try:
            with open(codeowners_path) as f:
                lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    pattern = parts[0]
                    owner_list = parts[1:]
                    # Check if any touched file matches this pattern
                    import fnmatch
                    for tf in touched_files:
                        if fnmatch.fnmatch(tf["path"], pattern):
                            owners.append({
                                "path_pattern": pattern,
                                "owners": owner_list,
                            })
                            break
        except IOError:
            pass

    return owners


def get_linked_issues(repo_root, pr_number=None, pr_description=""):
    """Attach linked issue/task text if available."""
    issues = []

    # Parse issue references from PR description (#123, org/repo#123)
    issue_refs = re.findall(r"#(\d+)", pr_description)

    for ref in issue_refs[:5]:  # Limit to 5 to avoid excessive API calls
        stdout, _, rc = run_cmd(
            f"gh issue view {ref} --json number,title,body,labels",
            retries=2, backoff_base=2
        )
        if rc == 0:
            try:
                issue = json.loads(stdout)
                issues.append({
                    "number": issue.get("number"),
                    "title": issue.get("title", ""),
                    "body": issue.get("body", ""),
                    "labels": [l.get("name", "") for l in issue.get("labels", [])],
                })
            except json.JSONDecodeError:
                pass

    return issues


def get_pr_metadata(pr_number):
    """Fetch PR title, description, and labels from GitHub API."""
    if not pr_number:
        return {"number": None, "title": "", "description": "", "labels": []}

    stdout, _, rc = run_cmd(
        f"gh pr view {pr_number} --json number,title,body,labels",
        retries=2, backoff_base=2
    )
    if rc == 0:
        try:
            pr = json.loads(stdout)
            return {
                "number": pr.get("number"),
                "title": pr.get("title", ""),
                "description": pr.get("body", ""),
                "labels": [l.get("name", "") for l in pr.get("labels", [])],
            }
        except json.JSONDecodeError:
            pass

    # Fallback: partial data from local git
    stdout, _, _ = run_cmd("git log -1 --format=%s HEAD")
    return {
        "number": pr_number,
        "title": stdout or "",
        "description": "",
        "labels": [],
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Collect PR context")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--pr-number", type=int, default=None, help="PR number")
    parser.add_argument("--base-branch", default="origin/main", help="Base branch")
    parser.add_argument("--output", default="-", help="Output file (- for stdout)")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo_root)

    # Collect PR metadata
    pr_metadata = get_pr_metadata(args.pr_number)

    # Parse diff
    diff_stats, touched_files = parse_diff_stats(repo_root, args.base_branch)

    # Infer subsystems
    subsystems = infer_subsystems(repo_root, touched_files)

    # Find related tests
    related_tests = find_related_tests(repo_root, touched_files)

    # Extract owners
    owners = extract_owners(repo_root, touched_files)

    # Linked issues
    linked_issues = get_linked_issues(
        repo_root, args.pr_number, pr_metadata.get("description", "")
    )

    # Detect AI authorship
    stdout, _, _ = run_cmd(
        f"python3 {os.path.dirname(__file__)}/detect_ai_authorship.py "
        f"--repo-root {repo_root} --base-branch {args.base_branch} --format json"
    )
    try:
        ai_authorship = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        ai_authorship = {"ai_assisted": False, "ai_tools": [], "ai_commit_ratio": 0.0}

    # Get raw diff
    raw_diff, _, _ = run_cmd(
        f"git -C {repo_root} diff {args.base_branch}...HEAD"
    )

    result = {
        "pr": pr_metadata,
        "diff_stats": diff_stats,
        "touched_files": touched_files,
        "subsystems": subsystems,
        "linked_issues": linked_issues,
        "related_tests": related_tests,
        "owners": owners,
        "ai_authorship": ai_authorship,
        "raw_diff": raw_diff,
    }

    output = json.dumps(result, indent=2)
    if args.output == "-":
        print(output)
    else:
        with open(args.output, "w") as f:
            f.write(output)


if __name__ == "__main__":
    main()
