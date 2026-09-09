---
name: ai-delegation-audit
description: >
  Static audit of a delegation config for 14 anti-patterns (AP1–AP14).
  Scans worker briefs, orchestrator config, context contract, and routing
  rules. Outputs severity-ranked findings with specific fixes. Can also
  refresh the evidence base (re-verify dated claims). Use when user says
  "my subagents keep fighting", "delegation is making it worse", "why is
  this so expensive", "agent output got worse after I added subagents",
  "audit my subagent config", "find delegation anti-patterns", "AP1 AP2
  AP3", "check my orchestrator for fan-out", "verify my cascade has eval gate",
  "is my relay allowed to commit", "touchedFiles guarantee".
---

# Audit — Delegation Anti-Pattern Scanner

Runs `../ai-delegation/scripts/audit_delegation.py` over your config. Finds what's broken.

---

## Process

### Step 1: Load References

- `../ai-delegation/references/anti-patterns.md` — 14 named failure modes (AP1–AP14) with detection + fix
- `../ai-delegation/references/evidence.md` — for claim provenance in findings

### Step 2: Accept Config Input

Input: path to config file (YAML/JSON) or directory.

Supported config shapes:
- Single file with `workers`, `orchestrator`, `context_contract` keys
- Directory of worker/orchestrator markdown files (best-effort aggregation)

### Step 3: Run Checks

For each anti-pattern AP1–AP14:

| ID | Name | Checks |
|----|------|--------|
| AP1 | Vague Worker Brief | Every worker has objective, output_format, tool_guidance, task_boundaries |
| AP2 | Uncapped Fan-Out | context_contract.fan_out_cap exists and ≤10 |
| AP3 | Verbose Worker Returns | worker.return_format ∈ {summary_artifact_ref, summary_artifact_ref_confidence} |
| AP4 | Orchestrator Doing Worker Work | orchestrator.executes_inline == false |
| AP5 | Parallel Writes to Shared State | context_contract.parallel_writes_shared_state == false |
| AP6 | Shared Context Assumed | context_contract.assumes_shared_context == false |
| AP7 | Escalation by Weaker Model (P4) | If pattern==P4, primary_tier must be frontier |
| AP8 | Advisor Re-Reads Full Trace | If pattern==P4, advisor_receives_full_trace == false |
| AP9 | No Verification Gate | context_contract.verification_gate exists |
| AP10 | No Failure/Timeout Handling | Every worker has timeout_seconds and fallback_on_failure |
| AP11 | No Artifact-Passing Convention | context_contract.artifact_dir exists |
| AP12 | Routing Without Eval Gate | If pattern∈{P1,P2}, eval_gate exists |
| AP13 | Worker Commits / No Review-Before-Land (P6) | If pattern==P6: worker_can_commit == false AND review_before_land == true |
| AP14 | TouchedFiles Treated as Containment (P6) | If pattern==P6, touched_files_as_containment == false |

Also flag P6 configs whose `delegation_contract` hash does not match an approved contract — fail-closed binding (see `../ai-delegation/references/cross-cli-relay.md`).

### Step 4: Output Findings

JSON (or `--format markdown`):

```json
{
  "findings": [
    {
      "id": "AP1",
      "name": "Vague Worker Brief",
      "severity": "HIGH",
      "file": "config.yaml",
      "worker_index": 2,
      "evidence": "Missing required brief fields: output_format, task_boundaries",
      "fix": "Add objective, output_format, tool_guidance, task_boundaries to every worker brief. Use assets/templates/subagent-definition.md"
    }
  ],
  "summary": {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
}
```

### Step 5: Optional — Refresh Evidence (`--refresh`)

Re-verify dated claims in `evidence.md`:
- Check `refresh_due` dates
- For each overdue claim, attempt to re-fetch source
- Update confidence or mark `unverified`
- Write updated `evidence.md`

---

## Output Format

Default: JSON to stdout (or `--output` file).
With `--format markdown`: human-readable report.

---

## Discipline Gates

- **D3**: Finding output includes specific file + line + fix (not generic warning)
- **D7**: Checks delegation scoping — context contract completeness is AP1/AP2/AP3/AP9/AP11
- **E3**: Diagnose before retry — each finding has a specific fix, not "look into it"
- **E7**: Honest narration — findings include severity, evidence, and actionable fix