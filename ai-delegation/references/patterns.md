# The Six Delegation Patterns

This file defines the canonical patterns. The `decide` sub-skill outputs one of these (or "don't delegate") with role→tier assignments and a context contract. P1–P5 route work across *models*; P6 routes work across *processes* (separate coding-agent CLIs). See `cross-cli-relay.md` for the P6 mechanics and invariants.

---

## Pattern Taxonomy

| ID | Name | Shape | What It Raises | What It Costs | Best For |
|----|------|-------|----------------|---------------|----------|
| P1 | **Router** (Classify → One Model) | Per-request difficulty/capability classification → send to exactly one model | Quality floor at lower spend | Requires calibration data; silent regression risk | High-volume heterogeneous traffic; cost ceiling is the constraint |
| P2 | **Cascade** (Cheap-First → Verify → Escalate) | Cheap model answers → verifier/confidence gate accepts or escalates | **Only pattern that can beat a single frontier model on both cost AND quality** | Verifier false-accepts are real failures; needs eval gate | Routine-heavy workloads; cost is binding; quality floor must hold |
| P3 | **Orchestrator-Worker** (Frontier Plans → Cheap Workers Execute) | Frontier decomposes → parallel workers execute → frontier synthesizes | Quality ceiling (+90.2%), wall-clock (−90%) | **~15× tokens** — NOT a cost pattern | Breadth-first research, open-ended tasks exceeding context window, quality is binding |
| P4 | **Advisor / "Smart Friend"** (Cheap Leads → Escalates Up) | Cheap primary leads → escalates to frontier on demand | Cost when it works with symmetric models | **Weak primary owns escalation and is badly calibrated** — open training problem | Cross-frontier capability routing (NOT difficulty escalation) |
| P5 | **Plan-Then-Execute** ("Sidekick" / Frozen Spec → Persistent Worker) | Frontier freezes unambiguous spec → cheap persistent worker executes; revisions hit cached context | Best cost/quality ratio for coding; revisions at ~10% token cost | Useless if spec cannot be frozen | Coding tasks with clear specs; iterative work; cost matters |
| P6 | **Cross-CLI Relay** (Orchestrator Dispatches → Separate Agent CLI Executes) | Orchestrator writes a self-contained brief → relay launches a *different* coding-agent CLI (Codex, Cursor, opencode, aider…) headlessly → returns structured result + `touchedFiles` → orchestrator reviews the diff and lands the commit | Access to a *different* harness's tools/auth/model; fleet lanes bind work-types to implementers | Process spawn + poll latency; autonomy enforcement varies by CLI (some cannot be prevented from writing) | Work needing different tooling/auth than the orchestrator; bounded mechanical tasks returning a clean diff; capability routing across CLIs (C4) |

---

## Pattern Comparison Matrix

| Dimension | P1 Router | P2 Cascade | P3 Orchestrator-Worker | P4 Advisor | P5 Plan-Then-Execute | P6 Cross-CLI Relay |
|-----------|-----------|------------|------------------------|------------|---------------------|--------------------|
| Models per request | 1 | 1–2 (escalation) | Many (fan-out) | 1–2 (escalation) | 2 (spec writer + executor) | 1 per dispatch (target CLI) |
| Decision timing | Pre-request | During inference (gate) | Runtime (dynamic) | During inference | Pre-execution | Pre-execution (brief written first) |
| Quality effect | Holds floor | Can beat single frontier on both | Raises ceiling | Raises ceiling (if primary strong) | Holds quality if spec frozen | Holds floor of target CLI; diff reviewed before landing |
| Cost effect | Cuts spend | Cuts spend | **Increases spend ~15×** | Cuts spend (if primary strong) | Cuts spend significantly | Prices at target CLI's model (can approach zero with local endpoints) |
| Wall-clock | Baseline | + gate latency | Parallel = faster | + escalation latency | Sequential but cached | + spawn/poll latency per dispatch |
| Failure mode | Silent regression | False accepts | Orchestrator context overflow | Weak primary mis-calibrates | Ambiguity in spec | Unenforced autonomy (CLI writes despite plan mode); lost report tails |
| Hard requirement | Calibration data | Verifier eval gate | Effort-scaling rules + fan-out cap | Strong primary or cross-frontier | Frozen spec + persistent worker | Self-contained brief + relay contract + review-before-land |

---

## Cross-Cutting: Clean-Context Verifier

**Not a standalone pattern** — a mandatory gate for P1, P2, P3, P5.

| Finding | Source | Implication |
|---------|--------|-------------|
| Clean-context reviewer catches avg 2 bugs/PR, 58% severe | C1 | Independence beats capability — verifier does NOT need to be frontier |
| Verifier must NOT share context with generator | C1, C7 | Shared context = correlated blind spots |
| Verifier runs on clean context + output artifact only | C1 | This is the cheapest quality insurance |

---

## When Each Pattern Wins

- **P1 Router**: You have >100 req/day, heterogeneous difficulty, want to hold a quality floor at minimum cost. You have or can build a small eval set (50–500 cases).
- **P2 Cascade**: Same as P1 but you need the *only* pattern that can mathematically beat a single model on both axes. You can build a verifier and measure its false-accept rate.
- **P3 Orchestrator-Worker**: Task is breadth-first (many independent threads), exceeds context window, quality is the binding constraint, and you can pay 15× tokens. You MUST have effort-scaling rules and fan-out caps.
- **P4 Advisor**: ONLY when both models are frontier-tier (cross-frontier capability routing). Never with a weak primary — it's an open training problem.
- **P5 Plan-Then-Execute**: Coding tasks where you can write a frozen spec. The worker is persistent (revisions are cheap because of cached context). Best for "I know what I want built, I just don't want to write it."
  - **Variant — cheap-plans-first**: when the spec itself is uncertain, invert the planner: the *cheap* worker runs read-only (tool allowlist or sandbox), returns a plan + its open questions, and executes only after approval. Emits `gate: "full"` (see `decision-gate.md` Gate Depth). Grounded in PG1–PG3.
  - **Persistence caveat**: "persistent worker" is harness-dependent. If a session's permission mode must change mid-flow, most runtimes require a fresh session — the approved plan must carry the context between passes (PG2). `wire` emits the plan-transfer step explicitly.
- **P6 Cross-CLI Relay**: The work needs tools, auth, or a model the orchestrating harness doesn't have (e.g., dispatch to Codex/Cursor/aider because they hold different credentials or a local endpoint). Best for bounded mechanical tasks — migrations, refactors, removal sweeps — that come back as a clean diff you review before landing. Requires a self-contained brief (the implementer has no orchestrator chat history) and a review-first loop. See `cross-cli-relay.md`.

---

## Anti-Patterns (Patterns That Sound Like These But Aren't)

| Anti-pattern | Why it fails | Which pattern it mimics |
|--------------|--------------|------------------------|
| "Parallel workers without effort scaling" | Spawns 50 subagents for a trivial query | P3 |
| "Cascade with no verifier / no eval gate" | Silent regression; you don't know it's broken | P2 |
| "Advisor with a weak primary" | Primary can't know when it's out of depth | P4 |
| "Orchestrator doing worker work inline" | Defeats context isolation; no token savings | P3 |
| "Delegating without a context contract" | Worker gets wrong context or returns verbose noise | P3, P5 |
| "Router with no calibration data" | Guessing = silent regression | P1 |
| "Frozen spec that isn't actually frozen" | Worker relocates ambiguity | P5 |
| "Relay that commits" | Reviewer never sees the tree before it lands | P6 |
| "Cross-CLI brief that leans on orchestrator history" | The implementer has no chat history; it relocates confusion | P6, P5 |

---

## The "Don't Delegate" Outcome

The `decide` sub-skill MUST be able to output **`pattern: none`** with a reason. The three failure laws (see `decision-gate.md`) are the gates:

- **L1 Shared-context law**: Load-bearing upstream decisions can't be written down
- **L2 Implicit-decisions law**: Parallel writers make conflicting implicit choices
- **L3 Orchestrator-window law**: Fan-out + verbose returns overflow the orchestrator

If any law triggers → `pattern: none`, reason = the specific law.