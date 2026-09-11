# Decision Gate — 7 Questions → One Recommendation

This is the core logic of the `decide` sub-skill. Run the gate in order. First "yes" to a failure law = `pattern: none`. Otherwise, proceed to pattern selection.

---

## The Three Failure Laws (Hard Stops)

| Law | Question | If YES → `pattern: none`, reason |
|-----|----------|----------------------------------|
| **L1 — Shared-Context Law** (Cognition P1) | "Does this subtask's correctness depend on upstream decisions that cannot be fully written down in a context contract?" | `shared-context-load-bearing` — summaries are lossy; delegation destroys load-bearing tacit knowledge |
| **L2 — Implicit-Decisions Law** (Cognition P2) | "Will the children WRITE to shared state (files, DB, API) in parallel?" | `parallel-writes` — actions carry implicit decisions; parallel writers make conflicting ones → writes must stay single-threaded |
| **L3 — Orchestrator-Window Law** | "Would the number of subagents × their return size exceed the orchestrator's practical context budget (~50k tokens for synthesis)?" | `orchestrator-overflow` — the orchestrator's context is the scarce resource; cap fan-out, return summaries, park artifacts on filesystem |

**If none trigger, proceed to pattern selection.**

---

## Pattern Selection (Remaining Questions)

| # | Question | Answer → Leans Toward |
|---|----------|------------------------|
| 4 | **Can the spec be frozen?** (No ambiguity; worker executes unambiguous instructions) | **YES → P5 Plan-Then-Execute** (if coding) / P3 with frozen briefs |
|   | | **NO → resolve ambiguity first; delegating relocates confusion** |
| 5 | **Does total information exceed one context window?** | **YES → Strong case for P3 Orchestrator-Worker** (parallel exploration) |
| 6 | **Binding constraint — cost or wall-clock/quality?** | **Cost → P1 Router or P2 Cascade** |
|   | | **Wall-clock / quality ceiling → P3 Orchestrator-Worker** |
| 7 | **Can the child's output be verified deterministically (or with a clean-context verifier)?** | **NO → Add a verifier pass, or keep in-band** (all patterns need this) |
| 8 | **Does execution need a different harness/CLI than the orchestrator?** (Different tools, auth, or model — e.g., Codex holds credentials the orchestrator lacks, or a local endpoint via aider) | **YES → P6 Cross-CLI Relay** (see `cross-cli-relay.md`; review-first loop mandatory) |

---

## Decision Tree (Textual)

```
START
│
├─ L1? → YES → pattern: none, reason: "shared-context-load-bearing"
├─ L2? → YES → pattern: none, reason: "parallel-writes"
├─ L3? → YES → pattern: none, reason: "orchestrator-overflow"
│
├─ Different harness/CLI required? (Q8)
│   ├─ YES → P6 Cross-CLI Relay (self-contained brief + relay + review-before-land)
│   │        └─ If the target CLI also takes a frozen spec → brief may combine with P5 shape
│   └─ NO ↓
│
├─ Spec freezable?
│   ├─ YES → Is it coding?
│   │   ├─ YES → P5 Plan-Then-Execute (persistent sidekick)
│   │   └─ NO  → P3 with frozen briefs per worker
│   └─ NO  → READ-ONLY PLANNER FIRST (do not delegate yet):
│            cheap worker restricted to read-only tools/sandbox explores,
│            returns plan + every question the task did not answer;
│            you answer them → spec is now freezable → re-run from Q4
│            (mechanics: gate "full"; see "Gate Depth" below)
│
├─ Info > context window?
│   ├─ YES → Quality/wall-clock binding?
│   │   ├─ YES → P3 Orchestrator-Worker (MUST have effort-scaling + fan-out cap)
│   │   └─ NO  → P1 Router (cheaper) or P2 Cascade
│   └─ NO  → Cost binding?
│       ├─ YES → Have eval set + verifier?
│       │   ├─ YES → P2 Cascade (beats single model on both)
│       │   └─ NO  → P1 Router (hold quality floor)
│       └─ NO  → Single agent is fine
```

---

## Output Contract (What `decide` Emits)

```json
{
  "pattern": "P3" | "P1" | "P2" | "P4" | "P5" | "P6" | "none",
  "reason": "if none, which failure law; if pattern, why this one",
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
    "artifact_passing": "filesystem",
    "result_contract": "subagent-summary" | "delegate-relay.result.v1"
  },
  "verification_gate": {
    "type": "clean_context_reviewer" | "deterministic_check" | "confidence_threshold" | "diff_review",
    "acceptance_criteria": "..."
  },
  "escalation_trigger": "explicit condition for moving up a tier (never let weak model decide)",
  "warnings": ["if P4 used with weak primary: WARNING — open calibration problem", "if P6: read-only enforcement varies by CLI — check cross-cli-relay.md caveats"]
}
```

---

## The Hard Rules This Skill Enforces

1. **Delegate DOWN, not UP.** Strong→cheap beats cheap→strong on token accounting (advisor re-reads full transcript as fresh input; worker runs on clean/cached context). P4 is conditional and carries a warning.

2. **Never let the weaker model own the escalation decision.** The orchestrator/verifier decides when to escalate.

3. **Effort scaling is mandatory for P3.** Without explicit rules, agents spawn 50 subagents for trivial queries (A6).

4. **Artifacts to filesystem, summaries to context.** P3/P5: workers write outputs to files, return lightweight refs. Avoids "game of telephone" (A7).

5. **Fan-out cap is a hard number.** Default 5. Adjustable via context contract but never unbounded.

6. **Every delegation needs a verification gate.** No exceptions. The verifier runs on clean context.

7. **The relay never commits (P6).** Committing belongs to the reviewer, always. A delegated worker that lands its own changes bypasses the verification gate entirely (AP13).

8. **P6 briefs are self-contained.** The implementer CLI has no orchestrator chat history. A brief that leans on prior conversation relocates confusion instead of resolving it (L1 in process form).

9. **P6 enforcement is stated in the target CLI's own terms.** Whatever the CLI cannot enforce (e.g., some have no true read-only mode) is said plainly in the warnings — never assumed. `touchedFiles` is a review aid, not containment (AP14).

10. **Restrict the capability, don't ask nicely.** A prompt telling a worker not to write is not a gate. Gate depth "full" means a tool allowlist (subagent lane) or an OS/CLI sandbox (relay lane) — enforced, not requested (PG3, AP15).

11. **An empty plan is a failure, not a success.** Some runtimes fail silently and exit 0 with an empty result — reads like a valid empty plan. A verifier that accepts it has false-accepted (PG2, AP9 family). If the plan has no questions and no steps on a gate="full" run, treat the run as failed and re-dispatch.

---

## Gate Depth (calibrated effort for the pre-write gate)

Every "delegate" verdict also emits a `gate` value. Default to the cheapest that covers the risk (PG1: on well-specified tasks, a full gate bought nothing — the ungated agent was correct and cost 76k tokens vs 26k for the plan).

| Depth | What it is | When to use |
|-------|-----------|-------------|
| `none` | No pre-write gate; the verification gate (post-hoc) covers it | Specified work, single file, lookups. Most of the time. |
| `one-line` | Append to the brief: **"Report anything you decided that the task did not specify."** Surfaces implicit decisions without slowing anything | The everyday default for any delegation |
| `full` | Worker runs **read-only** (tool allowlist or sandbox), returns plan + questions, executes only after approval. If approval never comes, it never writes | Gate when: the change touches **more than 3 files**; you are **root-causing** rather than localizing; **requirements are still fuzzy**; **two agents work the same files**; the work is hard to unwind |

Mechanics for `full` (PG2):
- **Subagent lane**: restrict the child to read-only tools in its definition (allowlist, not denylist).
- **Relay lane (Codex)**: a session cannot pause, gain permissions, and resume — the read-only pass and the write pass are **two fresh runs**, with the approved plan carrying the context between them.
- **Approval**: the orchestrator approves the plan; on anything hard to unwind, a **human** approves — a model approving a model is a known limit.
- Read-only enforcement for a ready-made planner: if [plan-gate](https://github.com/AgriciDaniel/plan-gate) is installed, its `agents/plan-gate-planner.md` + `audit.sh` provide a tested Lane-A/Codex-B implementation; otherwise use your harness's own tool-allowlist primitive.

---

## Usage in `decide` Sub-Skill

The sub-skill walks the user through the 8 questions (or accepts a structured input), then emits the output contract above. If the user provides partial context, it asks clarifying questions until the gate can be evaluated.