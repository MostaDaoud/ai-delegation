# Anti-Patterns — 15 Named Failure Modes

The `audit` sub-skill scans a delegation config for these. Each has a severity (HIGH/MEDIUM/LOW), a detection rule, and a specific fix.

---

## AP1 — Vague Worker Brief
**Severity:** HIGH
**Detection:** Worker prompt lacks any of: objective, output format, tool guidance, task boundaries.
**Evidence:** A6 — vague briefs ("research the semiconductor shortage") caused duplicate work (1 subagent on 2021, 2 on 2025).
**Fix:** Every worker gets a structured brief with all four fields. Use `assets/templates/subagent-definition.md`.

## AP2 — Uncapped Fan-Out
**Severity:** HIGH
**Detection:** Orchestrator can spawn unbounded subagents; no explicit `fan_out_cap` in context contract.
**Evidence:** L3 — orchestrator context is the scarce resource; uncapped fan-out + verbose returns = degradation/stall.
**Fix:** Set `fan_out_cap` in context contract (default 5). Enforce in orchestrator instructions.

## AP3 — Verbose Worker Returns
**Severity:** HIGH
**Detection:** Worker returns full transcripts, raw tool outputs, or >2k tokens instead of summary + artifact ref.
**Evidence:** A7 — "game of telephone" through context; A7 fix: artifacts to filesystem, summaries to context.
**Fix:** Worker instructions: return `{summary, artifact_ref, confidence}`. Artifacts written to files.

## AP4 — Orchestrator Doing Worker Work Inline
**Severity:** HIGH
**Detection:** Orchestrator executes tasks it should delegate (file edits, searches, code generation).
**Evidence:** Defeats context isolation; no token savings; no parallelism.
**Fix:** Orchestrator instructions: "When a task spans multiple files or needs research: 1. Plan. 2. Dispatch. 3. Wait for summaries. 4. Synthesize."

## AP5 — Parallel Writes to Shared State
**Severity:** HIGH
**Detection:** Multiple subagents write to the same files/DB/API without worktree isolation or serialization.
**Evidence:** L2 / C2 / C5 — actions carry implicit decisions; parallel writers make conflicting ones. Writes must stay single-threaded.
**Fix:** Either single-thread writes, or isolate via worktree/copy per subagent. No shared mutable state.

## AP6 — Shared Context Assumed But Not Real
**Severity:** HIGH
**Detection:** Subagents expected to know each other's work or the full conversation history.
**Evidence:** C5 — "agents assume they share state with their children when they don't." C7 Principle 1: share full traces, not summaries.
**Fix:** Workers are isolated. If cross-worker context is needed, park it on filesystem and reference it.

## AP7 — Escalation Owned by Weaker Model (P4 Misapplied)
**Severity:** HIGH
**Detection:** Pattern P4 (Advisor) used with a weak primary model; the primary decides when to escalate.
**Evidence:** C3 — "how does a dumber model know it's at its limits?" — open training problem. P4 only works cross-frontier.
**Fix:** Default to P3/P5. If P4 used, require both models to be frontier-tier. Orchestrator/verifier owns escalation.

## AP8 — Advisor Pattern Re-Reading Full Transcript
**Severity:** MEDIUM
**Detection:** Advisor receives the full conversation history as fresh input tokens each call.
**Evidence:** P4 — cached tokens ≈ 10% of fresh input. Delegate down, don't escalate up. Advisor re-reads = expensive.
**Fix:** Use P3/P5 instead. If advisor needed, pass only the minimal context (diff, objective) not the full trace.

## AP9 — No Verification Gate
**Severity:** HIGH
**Detection:** Any delegation pattern without a clean-context verifier or deterministic acceptance check.
**Evidence:** C1 — clean-context reviewer catches 2 bugs/PR (58% severe). P2: false accepts are real failures. P5: spec frozen ≠ output correct.
**Fix:** Every worker output passes through a verification gate: deterministic check, confidence threshold, or clean-context reviewer.

## AP10 — No Failure/Timeout Handling
**Severity:** MEDIUM
**Detection:** No explicit behavior for worker timeout, crash, or empty return.
**Evidence:** C5 — "one stuck worker can hang the whole task." Need bounded execution + fallback.
**Fix:** Each worker call has a timeout. Orchestrator defines fallback: retry with better brief, escalate tier, or handle inline.

## AP11 — No Artifact-Passing Convention
**Severity:** MEDIUM
**Detection:** Workers pass large outputs through context; no filesystem artifact convention.
**Evidence:** A7 — subagent output to filesystem minimizes "game of telephone" and reduces token overhead.
**Fix:** Define artifact directory. Workers write to `{artifact_dir}/{worker_id}/`. Return `{artifact_ref, summary}`.

## AP12 — Routing With No Eval Gate
**Severity:** HIGH
**Detection:** P1 Router or P2 Cascade deployed without a pre-merge eval set (50–500 cases) measuring false-accept / silent regression.
**Evidence:** P5 — "silent quality regression is the hidden tax; 50–500 case eval gate is the mitigation." A4 — start with ~20 queries.
**Fix:** Ship an eval set with the config. Gate: eval must pass before deploy. Track quality metrics in production.

## AP13 — Worker Commits / No Review-Before-Land (P6)
**Severity:** HIGH
**Detection:** Cross-CLI dispatch (P6) where the implementer is not force-disabled from committing/staging, or the procedure lacks an explicit review-the-diff step before landing.
**Evidence:** DS1/DS2 — "the relay never commits; committing belongs to the reviewer." Aider commits by default (`--auto-commits`, `--dirty-commits` both default true) and must be force-disabled.
**Fix:** Force-disable commit/staging in the target CLI where supported; state the limitation where not. Procedure must be: dispatch → poll → review `git diff` → re-run gates → orchestrator lands the commit.

## AP14 — TouchedFiles Treated as Containment (P6)
**Severity:** HIGH
**Detection:** P6 config or procedure that treats `touchedFiles` (or any post-run `git status` report) as a guarantee that no other files were modified — especially for CLIs without an enforced read-only mode.
**Evidence:** DS2 — `touchedFiles` is post-run `git status`; it cannot show ignored files, reverted edits, or writes outside the repository. Grok Build cannot be prevented from writing headlessly; Command Code `--yolo` write is full-trust with no path restriction.
**Fix:** Treat `touchedFiles` as a review aid only. Where out-of-tree writes are unacceptable, isolate via worktree, container, or OS-enforced sandbox. State the CLI's enforcement limits explicitly in the brief/procedure.

## AP15 — Prompt-Only Write Restriction
**Severity:** HIGH
**Detection:** A `gate: "full"` (or any read-only expectation) enforced only by prompt text — "do not write any files" — with no tool allowlist, sandbox flag, or permission mode behind it.
**Evidence:** PG3 — "restrict the capability, do not ask the model nicely. A prompt telling a model not to write is not a gate, in any runtime."
**Fix:** Restrict with the runtime's own primitive: read-only `tools:` allowlist for a subagent lane; the CLI's sandbox/read-only mode (or an OS sandbox) for a relay lane. Verify with a probe dispatch that the worker cannot write. If the runtime offers no enforcement primitive, say so in the warnings and use a worktree/container instead.

---

## Severity Definitions

| Severity | Meaning |
|----------|---------|
| HIGH | Will cause silent quality loss, context overflow, or incorrect outputs in production |
| MEDIUM | Increases cost, reduces reliability, or creates maintenance burden |
| LOW | Style/maintainability; not a functional failure |

---

## Audit Output Format

```json
{
  "findings": [
    {
      "id": "AP1",
      "severity": "HIGH",
      "file": "path/to/config",
      "line": 42,
      "evidence": "Worker 'researcher' brief has no output_format field",
      "fix": "Add output_format: 'json with fields X, Y, Z' to worker brief"
    }
  ],
  "summary": {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
}
```