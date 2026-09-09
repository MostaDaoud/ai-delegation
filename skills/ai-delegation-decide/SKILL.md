---
name: ai-delegation-decide
description: >
  Run the 8-question delegation decision gate. Evaluates three failure laws
  (shared-context, implicit-decisions, orchestrator-window) and selects one
  of six patterns (Router, Cascade, Orchestrator-Worker, Advisor,
  Plan-Then-Execute, Cross-CLI Relay) with model tiers, context contract,
  gate depth, fan-out cap, and verification gate. Outputs a structured
  delegation decision or explicit "don't delegate" with the specific failure
  law. Gate depth scales effort: none, a one-line implicit-decision report,
  or a full read-only plan-first gate. Use when user says "should I delegate
  this", "is this a subagent task", "one agent or many", "do I need
  orchestration here", "which model for this task", "cheaper model tier",
  "what pattern fits this work", "delegate to another cli", "gate depth",
  "plan before it writes".
---
<!-- fable-discipline-gate:v1 -->

## Pre-flight gate: Fable Discipline (run FIRST)

Before executing any instruction below, adopt the Fable Mindset operating manual at
`C:\Users\mosta\.claude\skills\fable-mindset\SKILL.md`. Apply its Decision Loop
(GROUND -> REASON -> ACT -> OBSERVE -> RE-EVALUATE -> VERIFY -> NARRATE) and its
7 execution rules to every step of this skill. FD runs first; this skill's own
instructions begin only after the discipline is adopted.

# Decide — Delegation Decision Gate

Run the gate. Get a decision contract. Or learn why you shouldn't delegate.

---

## Process

### Step 1: Load References

Load on-demand:
- `../ai-delegation/references/evidence.md` — for confidence-qualified claims
- `../ai-delegation/references/patterns.md` — the six patterns + when each wins
- `../ai-delegation/references/decision-gate.md` — 7 questions, decision tree, output contract
- `../ai-delegation/references/model-tier-matrix.md` — role × capability → tier defaults

### Step 2: Run the 8-Question Gate

Ask the user (or accept structured input) for each gate question:

1. **L1 — Shared-Context Law**: "Does this subtask's correctness depend on upstream decisions that cannot be fully written down in a context contract?"
2. **L2 — Implicit-Decisions Law**: "Will the children WRITE to shared state (files, DB, API) in parallel?"
3. **L3 — Orchestrator-Window Law**: "Would the number of subagents × their return size exceed the orchestrator's practical context budget (~50k tokens for synthesis)?"
4. **Spec Freezable?**: "Can the task spec be frozen — no ambiguity, worker executes unambiguous instructions?"
5. **Info > Context Window?**: "Does the total information exceed one context window?"
6. **Binding Constraint**: "Is the binding constraint cost, or wall-clock/quality ceiling?"
7. **Verifiable?**: "Can the child's output be verified deterministically (or with a clean-context verifier)?"
8. **Different Harness/CLI?**: "Does execution need tools, auth, or a model the orchestrating harness doesn't have — e.g., a separate coding-agent CLI (Codex, Cursor, aider) or a local endpoint?"

**If any of L1/L2/L3 = YES → Output `pattern: none` with the specific law. STOP.**

### Step 3: Pattern Selection

Based on remaining answers:

| Different CLI? | Spec Freezable | Info > Ctx | Constraint | → Pattern |
|----------------|----------------|------------|------------|-----------|
| YES | — | — | — | **P6 Cross-CLI Relay** (self-contained brief + relay contract + review-before-land) |
| NO | YES (coding) | — | — | **P5 Plan-Then-Execute** (persistent sidekick) |
| NO | YES (non-code) | — | — | **P3** with frozen briefs |
| NO | NO | YES | Quality/Wall-clock | **P3 Orchestrator-Worker** (MUST have effort-scaling + fan-out cap) |
| NO | NO | YES | Cost | **P1 Router** or **P2 Cascade** |
| NO | NO | NO | Cost | **P1 Router** (cheaper) |
| NO | NO | NO | — | **Single agent** (don't delegate) |

**P4 Advisor**: ONLY if both primary and advisor are frontier-tier. Otherwise warn: "P4 with weak primary is an open calibration problem (C3)."
**P6 Cross-CLI Relay**: set `mechanism: "relay-cli"`, `result_contract: "delegate-relay.result.v1"`, and `verification_gate.type: "diff_review"`. Load `../ai-delegation/references/cross-cli-relay.md` for brief requirements and per-CLI autonomy caveats (aider commits by default; grok cannot be prevented from writing; `touchedFiles` is not containment).

### Step 4: Assign Model Tiers

Using `model-tier-matrix.md`:

| Role | Default Tier |
|------|-------------|
| Decomposition / Planning / Ambiguity / Synthesis | frontier |
| Execution (frozen spec) | cheapest that clears verifier |
| Verification / Review | mid (independence > capability) |
| Code Generation | mid (cheap degrades fastest) |
| Classify / Extract / Short Summary / Common Translate | cheap |

### Step 5: Emit Decision Contract

```json
{
  "pattern": "P1" | "P2" | "P3" | "P4" | "P5" | "P6" | "none",
  "reason": "if none: which failure law; if pattern: why this one",
  "mechanism": "subagent" | "relay-cli",
  "gate": "none" | "one-line" | "full",
  "model_tiers": {
    "decomposition": "frontier",
    "execution": "cheap",
    "verification": "mid",
    "synthesis": "frontier"
  },
  "context_contract": {
    "child_receives": ["objective", "output_format", "tool_guidance", "task_boundaries"],
    "child_returns": ["summary", "artifact_ref", "confidence"],
    "fan_out_cap": 5,
    "artifact_passing": "filesystem"
  },
  "verification_gate": {
    "type": "clean_context_reviewer" | "deterministic_check" | "confidence_threshold",
    "acceptance_criteria": "..."
  },
  "escalation_trigger": "explicit condition (never let weak model decide)",
  "warnings": ["if P4 with weak primary: WARNING — open calibration problem", "if gate=full on a well-specified task: WARNING — gate bought nothing in PG1; default to one-line"]
}
```

### Step 6: Assign Gate Depth (calibrated effort — default to the cheapest)

| Depth | Use when | Mechanics |
|-------|----------|-----------|
| `none` | Specified work, single file, lookups | Post-hoc verification gate covers it |
| `one-line` | **Everyday default** for any delegation | Append to the brief: "Report anything you decided that the task did not specify." |
| `full` | >3 files touched, root-causing (not localizing), fuzzy requirements, two agents on the same files, hard-to-unwind work | Worker runs **read-only by capability restriction** (tool allowlist / sandbox — never prompt-only, AP15), returns plan + questions, executes only after approval. Relay lane: read-only and write passes are two fresh runs; the plan carries context (PG2). Empty plan = failed run. |

If Q4 answered NO (spec not freezable), the read-only planner IS the resolution mechanism: dispatch `gate: "full"` first, user answers the questions, spec becomes freezable, then re-run pattern selection.

---

## Output Format

Returns the decision contract above as JSON. If invoked interactively, also prints a human-readable summary with the gate walkthrough.

---

## Discipline Gates

- **D1**: Names verification artifact — the decision contract itself is verified by `audit` sub-skill
- **D7**: **Primary** — every decision emits full `context_contract` (child receives/returns, fan-out cap, failure behavior)
- **E6**: Calibrated effort — MUST be able to output `pattern: none` with specific law