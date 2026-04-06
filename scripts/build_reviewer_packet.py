#!/usr/bin/env python3
"""
Build the final human-readable reviewer packet from all artifacts.

This is what the human reviewer actually sees. It must be scannable in under
30 seconds for green-lane, under 2 minutes for red-lane.
"""

import json
import sys


DISCLAIMER = (
    "> **This is an evidence-based review aid, not an approval.** "
    "The tile produces findings and questions. Humans produce decisions."
)


def build_tldr(evidence_pack, findings):
    """Build a 1-2 sentence TL;DR."""
    pr = evidence_pack.get("pr", {})
    risk = evidence_pack.get("risk", {})
    stats = evidence_pack.get("diff", {}).get("stats", {})

    lane = risk.get("lane", "unknown").upper()
    files = stats.get("files_changed", 0)
    non_suppressed = [f for f in findings if not f.get("suppressed", False)]
    finding_count = len(non_suppressed)

    critical = [f for f in non_suppressed if f.get("severity") == "critical"]

    summary = f"{files} files changed. Risk: **{lane}**."
    if critical:
        summary += f" {len(critical)} critical finding(s) require attention."
    elif finding_count > 0:
        summary += f" {finding_count} finding(s) surfaced."
    else:
        summary += " No findings surfaced."

    return summary


def build_risk_section(evidence_pack):
    """Build the risk section."""
    risk = evidence_pack.get("risk", {})
    authorship = evidence_pack.get("authorship", {})

    lane = risk.get("lane", "unknown").upper()
    factors = risk.get("factors", [])
    ai_assisted = authorship.get("ai_assisted", False)
    ai_tools = authorship.get("ai_tools", [])

    lines = [f"### Risk: {lane}"]

    if factors:
        lines.append("\nContributing factors:")
        for f in factors:
            files = ", ".join(f.get("files", [])[:3])
            if len(f.get("files", [])) > 3:
                files += f" (+{len(f['files']) - 3} more)"
            lines.append(f"- **{f['factor']}**: {files}")

    if ai_assisted:
        tools = ", ".join(ai_tools) if ai_tools else "unknown"
        ratio = authorship.get("ai_commit_ratio", 0)
        lines.append(f"\nAI-assisted: yes (tools: {tools}, {ratio:.0%} of commits)")
    else:
        lines.append("\nAI-assisted: no")

    return "\n".join(lines)


def build_verification_section(evidence_pack):
    """Build the verification status table."""
    verification = evidence_pack.get("verification", {})
    verifiers = verification.get("verifiers", [])

    if not verifiers:
        return "### Verification Status\n\nNo verifiers discovered."

    lines = ["### Verification Status", ""]
    lines.append("| Verifier | Status | Notable findings |")
    lines.append("|----------|--------|-----------------|")

    for v in verifiers:
        status = v.get("status", "unknown")
        status_icon = {
            "pass": "PASS", "fail": "**FAIL**", "warn": "WARN",
            "skipped": "SKIP", "timeout": "TIMEOUT",
        }.get(status, status)

        notable = ""
        findings = v.get("findings", [])
        if findings:
            # Show first finding as summary
            first = findings[0]
            msg = first.get("message", "")[:80]
            count_note = f" (+{len(findings)-1} more)" if len(findings) > 1 else ""
            notable = f"{msg}{count_note}"

        lines.append(f"| {v['name']} | {status_icon} | {notable} |")

    return "\n".join(lines)


def build_findings_section(findings):
    """Build the findings section."""
    non_suppressed = [f for f in findings if not f.get("suppressed", False)]

    if not non_suppressed:
        return "### Findings (0 items)\n\nNo findings cleared the evidence threshold."

    lines = [f"### Findings ({len(non_suppressed)} items)", ""]

    for i, f in enumerate(non_suppressed, 1):
        severity = f.get("severity", "unknown").upper()
        confidence = f.get("merged_confidence", f.get("confidence", "unknown"))
        title = f.get("title", "Untitled finding")
        file_path = f.get("file", "")
        line_start = f.get("line_start")
        line_ref = f"{file_path}:{line_start}" if line_start else file_path

        lines.append(f"**{i}. [{severity}] {title}**")
        lines.append(f"- Location: `{line_ref}`")
        lines.append(f"- Why it matters: {f.get('why_it_matters', '')}")

        evidence = f.get("evidence", {})
        lines.append(f"- Evidence: {evidence.get('type', 'unknown')} — {evidence.get('detail', '')}")

        action = f.get("action", "verify")
        lines.append(f"- Suggested action: **{action}**")

        # Corroboration/conflict info
        corroborated = f.get("corroborated_by", [])
        contested = f.get("contested_by", [])
        if corroborated:
            lines.append(f"- Corroborated by: {', '.join(corroborated)}")
        if contested:
            lines.append(f"- **Contested by: {', '.join(contested)}** (requires human judgment)")

        lines.append("")

    return "\n".join(lines)


def build_assumptions_section(evidence_pack, findings):
    """Build the unresolved assumptions section."""
    assumptions = []

    # Missing artifacts are unresolved assumptions
    for ma in evidence_pack.get("missing_artifacts", []):
        if ma.get("required", False):
            assumptions.append(
                f"**Missing: {ma['artifact']}** — {ma['why_required']} "
                f"(suggested location: {ma.get('suggested_location', 'PR description')})"
            )

    # Findings requiring human judgment
    human_findings = [
        f for f in findings
        if f.get("requires_human", False) and not f.get("suppressed", False)
    ]
    for f in human_findings:
        assumptions.append(
            f"**{f.get('title', 'Finding')}** requires human judgment — "
            f"the tile cannot determine intent or correctness here"
        )

    # Low confidence risk classification
    risk = evidence_pack.get("risk", {})
    if risk.get("confidence") == "low":
        assumptions.append(
            "**Risk classification confidence is low** — "
            "lane was escalated as a precaution. Human should validate the actual risk level."
        )

    if not assumptions:
        return "### Unresolved Assumptions\n\nNone."

    lines = ["### Unresolved Assumptions", ""]
    for a in assumptions:
        lines.append(f"- {a}")

    return "\n".join(lines)


def build_focus_section(evidence_pack):
    """Build the recommended review focus section."""
    hotspots = evidence_pack.get("hotspots", [])
    risk_hotspots = [h for h in hotspots if h.get("risk_contributing", False)]

    if not hotspots:
        return "### Recommended Review Focus\n\nNo specific focus areas identified."

    # Prioritize risk-contributing hotspots
    focus = risk_hotspots if risk_hotspots else hotspots[:5]

    lines = ["### Recommended Review Focus", ""]
    for h in focus:
        file_path = h.get("file", "")
        start = h.get("line_start", "")
        end = h.get("line_end", "")
        line_ref = f"{file_path}:{start}-{end}" if start != end else f"{file_path}:{start}"
        lines.append(f"- `{line_ref}` — {h.get('category', '')}: {h.get('why', '')}")

    return "\n".join(lines)


def build_metadata_section(evidence_pack, reviewer_mode="fresh_eyes"):
    """Build the metadata section."""
    authorship = evidence_pack.get("authorship", {})
    wall_clock = evidence_pack.get("wall_clock_ms", 0)

    lines = [
        "### Metadata",
        f"- Reviewer mode: {reviewer_mode}",
        f"- Authoring model family: {', '.join(authorship.get('ai_tools', [])) or 'unknown'}",
        f"- Wall-clock time: {wall_clock}ms",
    ]

    return "\n".join(lines)


def build_packet(evidence_pack, findings, reviewer_mode="fresh_eyes"):
    """Build the complete reviewer packet."""
    sections = [
        "## PR Review Packet",
        "",
        DISCLAIMER,
        "",
        "### TL;DR",
        build_tldr(evidence_pack, findings),
        "",
        build_risk_section(evidence_pack),
        "",
        build_verification_section(evidence_pack),
        "",
        build_findings_section(findings),
        "",
        build_assumptions_section(evidence_pack, findings),
        "",
        build_focus_section(evidence_pack),
        "",
        build_metadata_section(evidence_pack, reviewer_mode),
    ]

    return "\n".join(sections)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build reviewer packet")
    parser.add_argument("--evidence-pack", required=True, help="Path to evidence pack JSON")
    parser.add_argument("--findings", required=True, help="Path to synthesized findings JSON")
    parser.add_argument("--reviewer-mode", default="fresh_eyes",
                        choices=["fresh_eyes", "challenger", "aggregated"])
    parser.add_argument("--output", default="-", help="Output file (- for stdout)")
    args = parser.parse_args()

    with open(args.evidence_pack) as f:
        evidence_pack = json.load(f)
    with open(args.findings) as f:
        findings = json.load(f)

    packet = build_packet(evidence_pack, findings, args.reviewer_mode)

    if args.output == "-":
        print(packet)
    else:
        with open(args.output, "w") as f:
            f.write(packet)


if __name__ == "__main__":
    main()
