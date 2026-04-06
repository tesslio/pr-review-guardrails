#!/usr/bin/env python3
"""
Collapse repeated findings from tools and reviewers into one canonical finding.

Deduplication strategy:
- exact match: same file, same line range, same issue -> merge, keep strongest evidence
- semantic overlap: different wording, same underlying issue -> merge, cite both sources
- corroboration: multiple independent sources flag the same area -> boost confidence
- conflict: two reviewers disagree -> surface both, mark as contested
"""

import json
import sys
from difflib import SequenceMatcher


CONFIDENCE_ORDER = {"high": 3, "medium": 2, "low": 1}
SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def lines_overlap(a_start, a_end, b_start, b_end, tolerance=3):
    """Check if two line ranges overlap or are within tolerance lines of each other."""
    if a_start is None or b_start is None:
        return False
    a_end = a_end or a_start
    b_end = b_end or b_start
    return (a_start - tolerance) <= b_end and (b_start - tolerance) <= a_end


def text_similarity(a, b):
    """Simple text similarity ratio."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def stronger_confidence(a, b):
    """Return the higher confidence level."""
    if CONFIDENCE_ORDER.get(a, 0) >= CONFIDENCE_ORDER.get(b, 0):
        return a
    return b


def stronger_severity(a, b):
    """Return the higher severity level."""
    if SEVERITY_ORDER.get(a, 0) >= SEVERITY_ORDER.get(b, 0):
        return a
    return b


def find_duplicates(findings):
    """
    Group findings into clusters of duplicates/overlaps.

    Returns list of clusters, where each cluster is a list of finding indices.
    """
    n = len(findings)
    visited = [False] * n
    clusters = []

    for i in range(n):
        if visited[i]:
            continue
        cluster = [i]
        visited[i] = True

        for j in range(i + 1, n):
            if visited[j]:
                continue

            fi = findings[i]
            fj = findings[j]

            # Must be in the same file
            if fi.get("file") != fj.get("file"):
                continue

            # Check line overlap
            overlap = lines_overlap(
                fi.get("line_start"), fi.get("line_end"),
                fj.get("line_start"), fj.get("line_end"),
            )

            # Check title/description similarity
            title_sim = text_similarity(
                fi.get("title", ""), fj.get("title", "")
            )
            why_sim = text_similarity(
                fi.get("why_it_matters", ""), fj.get("why_it_matters", "")
            )

            # Exact match: same file, overlapping lines, similar description
            if overlap and (title_sim > 0.7 or why_sim > 0.6):
                cluster.append(j)
                visited[j] = True
            # Semantic overlap: same file, very similar descriptions
            elif title_sim > 0.8 or why_sim > 0.8:
                cluster.append(j)
                visited[j] = True

        clusters.append(cluster)

    return clusters


def merge_cluster(findings, indices):
    """
    Merge a cluster of related findings into one canonical finding.

    Returns the merged finding with corroboration/conflict metadata.
    """
    if len(indices) == 1:
        finding = findings[indices[0]].copy()
        finding["corroborated_by"] = []
        finding["contested_by"] = []
        finding["merged_confidence"] = finding.get("confidence", "low")
        finding["suppressed"] = False
        finding["suppression_reason"] = None
        return finding

    cluster_findings = [findings[i] for i in indices]
    sources = [f.get("source", "unknown") for f in cluster_findings]

    # Pick the finding with strongest evidence as the canonical one
    canonical = max(
        cluster_findings,
        key=lambda f: (
            SEVERITY_ORDER.get(f.get("severity", "low"), 0),
            CONFIDENCE_ORDER.get(f.get("confidence", "low"), 0),
        ),
    )
    merged = canonical.copy()

    # Check for conflicts (different action recommendations on same code)
    actions = set(f.get("action", "") for f in cluster_findings)
    has_conflict = len(actions) > 1 and {"fix", "discuss"}.issubset(actions)

    if has_conflict:
        # Mark as contested
        merged["contested_by"] = [
            f.get("source", "unknown")
            for f in cluster_findings
            if f.get("action") != canonical.get("action")
        ]
        merged["corroborated_by"] = [
            f.get("source", "unknown")
            for f in cluster_findings
            if f.get("action") == canonical.get("action")
            and f is not canonical
        ]
        merged["merged_confidence"] = canonical.get("confidence", "low")
    else:
        # Corroboration — boost confidence
        merged["corroborated_by"] = [
            f.get("source", "unknown")
            for f in cluster_findings
            if f is not canonical
        ]
        merged["contested_by"] = []

        # Boost confidence if multiple independent sources agree
        if len(set(sources)) > 1:
            base = canonical.get("confidence", "low")
            if base == "low":
                merged["merged_confidence"] = "medium"
            elif base == "medium":
                merged["merged_confidence"] = "high"
            else:
                merged["merged_confidence"] = "high"
        else:
            merged["merged_confidence"] = canonical.get("confidence", "low")

    # Merge the strongest severity
    merged["severity"] = max(
        (f.get("severity", "low") for f in cluster_findings),
        key=lambda s: SEVERITY_ORDER.get(s, 0),
    )

    merged["suppressed"] = False
    merged["suppression_reason"] = None

    return merged


def suppress_weak_findings(findings, verifier_findings=None):
    """
    Suppress findings that don't meet the evidence threshold.

    - Style-only findings already covered by linters
    - Weak speculation without concrete evidence
    """
    linter_files = set()
    if verifier_findings:
        for vf in verifier_findings:
            if vf.get("name") in ("linter", "static-analysis"):
                for f in vf.get("findings", []):
                    linter_files.add(f.get("file", ""))

    for finding in findings:
        # Suppress style findings on files already covered by linter
        evidence_type = finding.get("evidence", {}).get("type", "")
        if evidence_type == "contextual_reasoning":
            confidence = finding.get("merged_confidence", finding.get("confidence", "low"))
            if confidence == "low":
                finding["suppressed"] = True
                finding["suppression_reason"] = "low-confidence contextual reasoning below evidence threshold"

    return findings


def dedupe(findings, verifier_results=None):
    """Main deduplication pipeline."""
    if not findings:
        return []

    clusters = find_duplicates(findings)
    merged = [merge_cluster(findings, cluster) for cluster in clusters]
    merged = suppress_weak_findings(merged, verifier_results)

    # Sort by severity x confidence (non-suppressed first)
    merged.sort(
        key=lambda f: (
            f.get("suppressed", False),
            -SEVERITY_ORDER.get(f.get("severity", "low"), 0),
            -CONFIDENCE_ORDER.get(f.get("merged_confidence", "low"), 0),
        )
    )

    return merged


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Deduplicate findings")
    parser.add_argument("--findings", required=True, nargs="+",
                        help="Paths to finding JSON files")
    parser.add_argument("--verifiers", help="Path to verifier results JSON")
    parser.add_argument("--output", default="-", help="Output file (- for stdout)")
    args = parser.parse_args()

    all_findings = []
    for path in args.findings:
        with open(path) as f:
            data = json.load(f)
            if isinstance(data, list):
                all_findings.extend(data)
            else:
                all_findings.append(data)

    verifier_results = None
    if args.verifiers:
        with open(args.verifiers) as f:
            verifier_data = json.load(f)
            verifier_results = verifier_data.get("verifiers", [])

    result = dedupe(all_findings, verifier_results)

    output = json.dumps(result, indent=2)
    if args.output == "-":
        print(output)
    else:
        with open(args.output, "w") as f:
            f.write(output)


if __name__ == "__main__":
    main()
