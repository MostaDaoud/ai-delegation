#!/usr/bin/env python3
"""
Purpose: Static audit of a delegation config for the 15 anti-patterns (AP1-AP15).
Input: Path to config directory or file (YAML/JSON) defining workers, orchestrator, routing.
Output: JSON findings with severity + fix; optional markdown report.
Usage: python scripts/audit_delegation.py <path> [--format json|markdown] [--output out.json]
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import re


# Anti-pattern definitions
ANTI_PATTERNS = [
    {
        "id": "AP1",
        "name": "Vague Worker Brief",
        "severity": "HIGH",
        "check": lambda w: not all(k in w and w[k] for k in ["objective", "output_format", "tool_guidance", "task_boundaries"]),
        "evidence": "Missing required brief fields: {missing}",
        "fix": "Add objective, output_format, tool_guidance, task_boundaries to every worker brief. Use assets/templates/subagent-definition.md",
    },
    {
        "id": "AP2",
        "name": "Uncapped Fan-Out",
        "severity": "HIGH",
        "check": lambda ctx: ctx.get("fan_out_cap") is None or ctx.get("fan_out_cap", 0) > 10,
        "evidence": "No fan_out_cap set or cap > 10 (current: {cap})",
        "fix": "Set fan_out_cap in context contract (default 5). Enforce in orchestrator instructions.",
    },
    {
        "id": "AP3",
        "name": "Verbose Worker Returns",
        "severity": "HIGH",
        "check": lambda w: w.get("return_format") not in ["summary_artifact_ref", "summary_artifact_ref_confidence"],
        "evidence": "Worker return_format is '{fmt}' — should be 'summary_artifact_ref' or 'summary_artifact_ref_confidence'",
        "fix": "Worker instructions: return {{summary, artifact_ref, confidence}}. Artifacts to filesystem.",
    },
    {
        "id": "AP4",
        "name": "Orchestrator Doing Worker Work",
        "severity": "HIGH",
        "check": lambda orch: orch.get("executes_inline", False) == True,
        "evidence": "Orchestrator configured to execute tasks inline instead of delegating",
        "fix": "Orchestrator instructions: Plan → Dispatch → Wait for summaries → Synthesize. Never execute inline.",
    },
    {
        "id": "AP5",
        "name": "Parallel Writes to Shared State",
        "severity": "HIGH",
        "check": lambda ctx: ctx.get("parallel_writes_shared_state", False) == True,
        "evidence": "Config allows parallel workers to write shared state without isolation",
        "fix": "Single-thread writes, or isolate via worktree/copy per worker. No shared mutable state.",
    },
    {
        "id": "AP6",
        "name": "Shared Context Assumed But Not Real",
        "severity": "HIGH",
        "check": lambda ctx: ctx.get("assumes_shared_context", False) == True,
        "evidence": "Config assumes workers share context / know each other's work",
        "fix": "Workers are isolated. Park shared info on filesystem and reference it explicitly.",
    },
    {
        "id": "AP7",
        "name": "Escalation Owned by Weaker Model (P4 Misapplied)",
        "severity": "HIGH",
        "check": lambda ctx: ctx.get("pattern") == "P4" and ctx.get("primary_tier") != "frontier",
        "evidence": "Pattern P4 (Advisor) used with primary_tier='{tier}' — only works cross-frontier",
        "fix": "Default to P3/P5. If P4 used, require both primary and advisor to be frontier-tier.",
    },
    {
        "id": "AP8",
        "name": "Advisor Re-Reading Full Transcript",
        "severity": "MEDIUM",
        "check": lambda ctx: ctx.get("pattern") == "P4" and ctx.get("advisor_receives_full_trace", False),
        "evidence": "Advisor receives full conversation history as fresh input tokens",
        "fix": "Use P3/P5 instead. If advisor needed, pass minimal context (diff, objective) only.",
    },
    {
        "id": "AP9",
        "name": "No Verification Gate",
        "severity": "HIGH",
        "check": lambda ctx: not ctx.get("verification_gate"),
        "evidence": "No verification_gate defined in context contract",
        "fix": "Every worker output must pass a verification gate: deterministic_check, confidence_threshold, or clean_context_reviewer.",
    },
    {
        "id": "AP10",
        "name": "No Failure/Timeout Handling",
        "severity": "MEDIUM",
        "check": lambda w: not w.get("timeout_seconds") or not w.get("fallback_on_failure"),
        "evidence": "Worker missing timeout_seconds or fallback_on_failure",
        "fix": "Add timeout_seconds (default 300) and fallback_on_failure (retry_with_better_brief | escalate_tier | handle_inline).",
    },
    {
        "id": "AP11",
        "name": "No Artifact-Passing Convention",
        "severity": "MEDIUM",
        "check": lambda ctx: not ctx.get("artifact_dir"),
        "evidence": "No artifact_dir defined for worker outputs",
        "fix": "Define artifact_dir (e.g., .opencode/artifacts/{{worker_id}}/). Workers write artifacts, return refs.",
    },
    {
        "id": "AP12",
        "name": "Routing With No Eval Gate",
        "severity": "HIGH",
        "check": lambda ctx: ctx.get("pattern") in ["P1", "P2"] and not ctx.get("eval_gate"),
        "evidence": "Pattern {pattern} deployed without eval_gate (pre-merge eval set)",
        "fix": "Ship an eval set (50-500 cases) with the config. Gate: eval must pass before deploy. Track quality in prod.",
    },
    {
        "id": "AP13",
        "name": "Worker Commits / No Review-Before-Land (P6)",
        "severity": "HIGH",
        "check": lambda ctx: ctx.get("pattern") == "P6" and (ctx.get("worker_can_commit", True) or not ctx.get("review_before_land", False)),
        "evidence": "P6 dispatch without review_before_land, or implementer not force-disabled from committing",
        "fix": "Force-disable commit/staging in the target CLI where supported. Procedure: dispatch -> poll -> review git diff -> re-run gates -> orchestrator lands the commit.",
    },
    {
        "id": "AP14",
        "name": "TouchedFiles Treated as Containment (P6)",
        "severity": "HIGH",
        "check": lambda ctx: ctx.get("pattern") == "P6" and ctx.get("touched_files_as_containment", False),
        "evidence": "Config treats touchedFiles/post-run git status as a guarantee no other files were modified",
        "fix": "Treat touchedFiles as a review aid only. Where out-of-tree writes are unacceptable, isolate via worktree/container/OS sandbox. State CLI enforcement limits explicitly.",
    },
    {
        "id": "AP15",
        "name": "Prompt-Only Write Restriction",
        "severity": "HIGH",
        "check": lambda ctx: (ctx.get("gate") == "full" or ctx.get("read_only_expected", False)) and ctx.get("read_only_enforced", True) is False or ctx.get("write_restriction") == "prompt",
        "evidence": "Read-only expectation (gate=full or read_only_expected) enforced only by prompt text: write_restriction=prompt or read_only_enforced=false",
        "fix": "Restrict with the runtime's primitive: read-only tools allowlist (subagent lane) or CLI/OS sandbox (relay lane). Verify with a probe dispatch. If no primitive exists, use a worktree/container and say so in warnings.",
    },
]


def load_config(path: Path) -> Dict[str, Any]:
    """Load config from file or directory."""
    if path.is_file():
        if path.suffix in [".yaml", ".yml"]:
            try:
                import yaml
                with open(path) as f:
                    return yaml.safe_load(f)
            except ImportError:
                print("PyYAML not installed; install with: pip install pyyaml", file=sys.stderr)
                sys.exit(1)
        elif path.suffix == ".json":
            with open(path) as f:
                return json.load(f)
        else:
            # Try JSON first, then YAML
            try:
                with open(path) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                try:
                    import yaml
                    with open(path) as f:
                        return yaml.safe_load(f)
                except Exception:
                    print(f"Could not parse {path} as JSON or YAML", file=sys.stderr)
                    sys.exit(1)
    else:
        # Directory: look for common config files
        for name in ["delegation.yaml", "delegation.yml", "delegation.json",
                     "routing.yaml", "routing.yml", "routing.json",
                     "config.yaml", "config.yml", "config.json"]:
            f = path / name
            if f.exists():
                return load_config(f)
        # Try to aggregate from subagent files
        return aggregate_from_dir(path)


def aggregate_from_dir(path: Path) -> Dict[str, Any]:
    """Best-effort aggregation from a directory of worker/orchestrator files."""
    result = {"workers": [], "orchestrator": {}, "context_contract": {}}
    for f in path.rglob("*.md"):
        content = f.read_text()
        # Look for worker definitions
        if "worker" in f.name.lower() or "subagent" in f.name.lower():
            result["workers"].append(parse_worker_from_md(content, f))
        elif "orchestrator" in f.name.lower() or "lead" in f.name.lower():
            result["orchestrator"] = parse_orchestrator_from_md(content, f)
    return result


def parse_worker_from_md(content: str, path: Path) -> Dict[str, Any]:
    """Extract worker config from markdown."""
    w = {"source_file": str(path)}
    # Look for key fields
    for field in ["objective", "output_format", "tool_guidance", "task_boundaries",
                  "return_format", "timeout_seconds", "fallback_on_failure", "verification_gate"]:
        match = re.search(rf"{field}[:]\s*([^\n]+)", content, re.IGNORECASE)
        if match:
            w[field] = match.group(1).strip()
    return w


def parse_orchestrator_from_md(content: str, path: Path) -> Dict[str, Any]:
    """Extract orchestrator config from markdown."""
    o = {"source_file": str(path)}
    for field in ["executes_inline", "fan_out_cap", "pattern", "primary_tier",
                  "verification_gate", "artifact_dir", "eval_gate", "advisor_receives_full_trace",
                  "parallel_writes_shared_state", "assumes_shared_context"]:
        match = re.search(rf"{field}[:]\s*([^\n]+)", content, re.IGNORECASE)
        if match:
            val = match.group(1).strip().lower()
            if val in ["true", "yes", "1"]:
                o[field] = True
            elif val in ["false", "no", "0"]:
                o[field] = False
            else:
                o[field] = val
    return o


def run_audit(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run all anti-pattern checks against the config."""
    findings = []

    workers = config.get("workers", [])
    orchestrator = config.get("orchestrator", {})
    context = config.get("context_contract", {})

    # Merge context into orchestrator for checks that need both
    merged = {**orchestrator, **context}
    merged["workers"] = workers

    for ap in ANTI_PATTERNS:
        try:
            # Determine what to check
            if ap["id"] in ["AP1", "AP3", "AP10"]:
                # Per-worker checks
                for i, w in enumerate(workers):
                    if ap["check"](w):
                        missing = [k for k in ["objective", "output_format", "tool_guidance", "task_boundaries"]
                                   if k not in w or not w[k]]
                        evidence = ap["evidence"].format(
                            missing=", ".join(missing) if missing else "unknown",
                            fmt=w.get("return_format", "undefined"),
                            cap=merged.get("fan_out_cap", "undefined"),
                            tier=merged.get("primary_tier", "undefined"),
                            pattern=merged.get("pattern", "undefined"),
                        )
                        findings.append({
                            "id": ap["id"],
                            "name": ap["name"],
                            "severity": ap["severity"],
                            "file": w.get("source_file", "unknown"),
                            "worker_index": i,
                            "evidence": evidence,
                            "fix": ap["fix"],
                        })
            else:
                # Context/orchestrator checks
                if ap["check"](merged):
                    evidence = ap["evidence"].format(
                        missing="",
                        fmt="",
                        cap=merged.get("fan_out_cap", "undefined"),
                        tier=merged.get("primary_tier", "undefined"),
                        pattern=merged.get("pattern", "undefined"),
                    )
                    findings.append({
                        "id": ap["id"],
                        "name": ap["name"],
                        "severity": ap["severity"],
                        "file": orchestrator.get("source_file", "unknown"),
                        "evidence": evidence,
                        "fix": ap["fix"],
                    })
        except Exception as e:
            # Don't let one broken check crash the audit
            findings.append({
                "id": ap["id"],
                "name": ap["name"],
                "severity": "LOW",
                "file": "internal",
                "evidence": f"Check failed: {e}",
                "fix": "Review anti-pattern definition",
            })

    return findings


def format_markdown(findings: List[Dict[str, Any]]) -> str:
    """Format findings as markdown."""
    if not findings:
        return "# Audit Results\n\n✅ No anti-patterns found.\n"

    by_severity = {"HIGH": [], "MEDIUM": [], "LOW": []}
    for f in findings:
        by_severity[f["severity"]].append(f)

    md = ["# Delegation Audit Results\n"]
    for sev in ["HIGH", "MEDIUM", "LOW"]:
        items = by_severity[sev]
        if items:
            md.append(f"## {sev} ({len(items)})")
            for f in items:
                md.append(f"### {f['id']}: {f['name']}")
                md.append(f"- **File:** `{f['file']}`")
                if "worker_index" in f:
                    md.append(f"- **Worker:** #{f['worker_index']}")
                md.append(f"- **Evidence:** {f['evidence']}")
                md.append(f"- **Fix:** {f['fix']}")
                md.append("")

    summary = {k: len(v) for k, v in by_severity.items()}
    md.append(f"## Summary\n- HIGH: {summary['HIGH']}\n- MEDIUM: {summary['MEDIUM']}\n- LOW: {summary['LOW']}")
    return "\n".join(md)


def main(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config(Path(args.path))

    findings = run_audit(config)

    output = {
        "findings": findings,
        "summary": {
            "HIGH": sum(1 for f in findings if f["severity"] == "HIGH"),
            "MEDIUM": sum(1 for f in findings if f["severity"] == "MEDIUM"),
            "LOW": sum(1 for f in findings if f["severity"] == "LOW"),
        },
    }

    if args.format == "markdown":
        md = format_markdown(findings)
        if args.output:
            with open(args.output, "w") as f:
                f.write(md)
            print(f"Markdown report written to {args.output}", file=sys.stderr)
        else:
            print(md)
    else:
        if args.output:
            with open(args.output, "w") as f:
                json.dump(output, f, indent=2)
            print(f"JSON written to {args.output}", file=sys.stderr)
        else:
            json.dump(output, sys.stdout, indent=2)

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit delegation config for anti-patterns")
    parser.add_argument("path", help="Path to config file or directory")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    try:
        main(args)
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)