# Cross-CLI Relay — P6 Mechanics, Invariants, and Contracts

P6 routes a task to a **separate coding-agent CLI process** (Codex, Cursor Agent, opencode, aider, grok, Kimi, Claude Code itself, …) instead of an in-harness subagent. The pattern is grounded in the [delegate-skills](https://github.com/amElnagdy/delegate-skills) architecture (DS1–DS3 in `evidence.md`). This file defines the mechanics this skill assumes; it does not ship relays — see "Relationship to relay implementations" below.

---

## The Review-First Loop (mandatory for every P6 dispatch)

```
1. WRITE THE BRIEF     Self-contained task context. The implementer has
                       NO orchestrator chat history (L1 in process form).
2. DISPATCH            Via a relay (or the CLI's own headless mode).
3. WAIT / POLL         Until the run completes; collect the result contract.
4. REVIEW THE DIFF     Re-run the project's gates yourself (tests, lint,
                       build). Read `git diff` — the diff IS the deliverable.
5. LAND IT             YOU commit. Committing belongs to the reviewer.
```

If any step is skipped — especially 4 or 5 — the dispatch is an AP13 violation.

---

## The Four Invariants (a P6 setup fails the audit without them)

| # | Invariant | Why |
|---|-----------|-----|
| 1 | **A separate CLI edits a real working tree, and the diff is the deliverable.** Not an API wrapper, not a gateway. | The whole point of P6 is a reviewable artifact, not prose output |
| 2 | **The relay never commits.** Committing belongs to the reviewer, always. | A worker that lands its own changes bypasses the verification gate (AP13) |
| 3 | **Relay scripts use platform built-ins only** — no dependencies, no network calls of their own, no credentials, no telemetry. | Dispatch infrastructure must not widen the trust surface |
| 4 | **Autonomy is stated in the target CLI's own terms**, and whatever the CLI cannot enforce is said plainly. | Some CLIs cannot be prevented from writing headlessly; assuming otherwise is AP14 territory |

---

## Result Contract — `delegate-relay.result.v1`

When `mechanism: "relay-cli"`, the `context_contract.child_returns` field should reference this shape. A P6 worker returns exactly this (plus the artifact ref):

```json
{
  "contract": "delegate-relay.result.v1",
  "status": "completed" | "failed" | "aborted" | "unavailable",
  "exitCode": 0,
  "signal": {"killed": false, "hint": "null | host-killed (e.g., OOM)"},
  "report": "implementer's own final report text",
  "touchedFiles": ["path/one", "path/two"],
  "sessionId": "resume-id-or-null"
}
```

**Consumption rules:**
- `status` + `exitCode` decide whether review even starts; a non-success status with exit 0 means "failed" — convert it, never trust the exit code alone.
- `touchedFiles` is derived from post-run `git status`. It **cannot show ignored files, reverted edits, or writes outside the repository**. It is a review aid, not containment (AP14).
- `sessionId` enables resume: follow-up dispatches send a **delta brief** ("amend the comment you just wrote") instead of repeating full context — this is the P6 analogue of P5's cached-context revisions.

---

## Brief Requirements (the P6 analogue of the worker brief)

A P6 brief must carry the same four fields as any worker brief (objective, output format, tool guidance, task boundaries — AP1 applies), **plus**:

1. **Self-contained**: no reference to "as discussed", no orchestrator history assumptions.
2. **Path-scoped**: name the exact files/directories in scope; state that writes outside them are out of scope.
3. **Gate statement**: name the gates the orchestrator will run post-dispatch (tests, lint) so the implementer can pre-run them.
4. **No commit instruction**: explicitly forbid the implementer from committing/staging (enforce with CLI flags where the CLI supports it; state the limitation where it doesn't).

---

## Autonomy Enforcement — Known Caveats (stated plainly, per Invariant 4)

These are real, measured limitations from the delegate-skills verification work (DS2). A `wire` config for P6 MUST surface the relevant one as a warning:

| Situation | Caveat | Handling |
|-----------|--------|----------|
| Aider | Commits by default (`--auto-commits`, `--dirty-commits` both default true) | Relay/config must force-disable both; never configurable away |
| Grok Build | Cannot be prevented from writing headlessly | Report a tri-state violation tripwire; never claim read-only |
| Several CLIs | No CLI-enforced read-only mode at all | `touchedFiles` + diff are what you review against, not a guarantee; use a worktree/container when writes outside the target tree are unacceptable |
| Command Code (`--yolo`) | Headless write is full-trust, no path restriction — brief path lists are guidance, not containment | Isolate via worktree; container/OS sandbox when out-of-tree writes are unacceptable |
| ZCode | CLI ships inside a desktop app; only `plan` and `yolo` modes work headlessly | Reject non-functional modes rather than report no-op as success |
| Long stream runs | Some CLIs discard queued stdout on exit; report tails can be lost | The diff is the deliverable; a thin report means missing information, not a failed run |

---

## Fleet Lanes (work-type → implementer binding)

When P6 is used for more than one work type, bind lanes — this is P1 routing applied at the process level:

```yaml
# fleet config (delegate-fleet.v1-compatible shape)
lanes:
  - name: feature
    implementer: codex        # target CLI
    dials: {model: gpt-5, sandbox: workspace-write}
  - name: tests
    implementer: cursor-agent
    dials: {read_only: false}
  - name: ui
    implementer: opencode
    dials: {model: <configured-at-wire-time>}
```

Rules (DS3):
- **Explicit flags override lane dials** — a one-off `--model` beats the lane default.
- **The wrong implementer skill for a lane fails loud**, not silent.
- **Project lane config is content-bound to explicit setup approval** — a cloned or hand-edited project config **fails closed** until re-approved. Our `wire` sub-skill mirrors this: emitted configs carry a decision-contract hash; configs without a matching approved contract fail closed.

---

## Gate Depth "full" over a Relay (PG2–PG3)

When the decision contract emits `gate: "full"` for a relay dispatch, the pre-write gate works differently per lane — and one property is universal:

- **Read-only pass and write pass are TWO FRESH RUNS.** A Codex session cannot pause, gain permissions, and resume (confirmed upstream, openai/codex#33974). The approved plan and the answered questions carry the context between passes — the brief for the write pass includes the plan verbatim plus your answers.
- **Empty plan = failure.** Some runtimes fail and exit 0 with an empty result that reads like a valid empty plan. A `gate: "full"` run whose plan has no steps and no questions is a failed run — re-dispatch (PG2).
- **Preflight the sandbox.** CLI sandboxes can silently no-op in some environments (e.g., inside an IDE Flatpak). Dispatch a trivial read-only probe first; treat an empty probe as "sandbox unavailable," not as an empty plan.
- **Enforcement, not request:** the read-only pass must be restricted by the CLI's own sandbox/read-only mode or an OS sandbox — never by a prompt instruction (AP15). If [plan-gate](https://github.com/AgriciDaniel/plan-gate) is installed, its `preflight` and `audit` commands provide tested implementations for the Codex lane.

---

## When P6 vs In-Harness Subagents (P3/P5)

| Signal | Choose |
|--------|--------|
| Work needs different auth/tools/credentials than orchestrator | **P6** |
| Target CLI holds a cheaper/local endpoint (near-zero marginal cost) | **P6** |
| Task is mechanical, bounded, returns a clean diff | **P6** |
| Worker must consume orchestrator context (rich, hard-to-write-down) | **P3/P5** (subagent) — P6 would force lossy serialization (L1) |
| Tight iteration loop with frequent revisions | **P5** (cached context) over P6 (fresh process per dispatch) |
| Fan-out parallelism with cheap tokens | **P3** |

---

## Relationship to Relay Implementations

This skill **decides and wires**; it does not ship CLIs relays. For actual dispatch:

- If [delegate-skills](https://github.com/amElnagdy/delegate-skills) is installed, its per-CLI `*-delegate` skills are the reference relays — `wire` emits briefs and lane configs compatible with their contract.
- If not, `wire` emits the brief + lane config + the dispatch/poll/review procedure, and the orchestrator uses the target CLI's documented headless mode directly.

Either way, the four invariants and the review-first loop are non-negotiable.
