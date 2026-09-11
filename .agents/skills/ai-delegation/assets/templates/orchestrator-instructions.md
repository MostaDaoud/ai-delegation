# Orchestrator Instructions Template

Paste this into your harness's top-level config (AGENTS.md, CLAUDE.md, GEMINI.md, etc.).

---

## Delegation Rules for {{ORCHESTRATOR_NAME}}

**Pattern:** {{PATTERN}} (P1-P6; P6 = Cross-CLI Relay, see references/cross-cli-relay.md)

### Core Instructions

When a task matches the delegation criteria below:

1. **PLAN FIRST.** Do not execute inline. Decompose the task into subtasks with explicit objectives, output formats, tool guidance, and boundaries.

2. **DISPATCH ONE WORKER PER INDEPENDENT SUBTASK.** Use the worker definitions emitted by the `wire` step for your harness. Each worker gets its own context window.

3. **WAIT FOR SUMMARIES.** Do not re-read worker transcripts. Collect `{summary, artifact_ref, confidence}` from each worker.

4. **SYNTHESIZE.** Combine worker summaries into a single coherent answer. Resolve conflicts. This is a reasoning step, not concatenation.

5. **VERIFY.** Before final output, run the verification gate defined in the context contract.

### Fan-Out Cap

**Maximum concurrent workers:** {{FAN_OUT_CAP}} (default: 5)

If more subtasks exist than the cap, prioritize by impact and batch sequentially.

### Effort Scaling (Mandatory for P3)

| Query Type | Worker Count | Tool Calls per Worker |
|------------|--------------|----------------------|
| Simple fact-find | 1 | 3–10 |
| Direct comparison | 2–4 | 10–15 each |
| Complex research | 5–{{FAN_OUT_CAP}} | 15–25 each |

**Never** exceed {{FAN_OUT_CAP}} workers. **Never** let a simple query spawn many workers.

### Artifact Convention

Workers write outputs to `.{{HARNESS}}/artifacts/{worker_id}/`.

You receive lightweight references. Read artifacts only when synthesis requires it.

### Verification Gate

{{VERIFICATION_GATE_INSTRUCTIONS}}

### Failure Handling

- Worker timeout → {{FALLBACK}}
- Worker returns empty/error → {{FALLBACK}}
- Verification fails → retry worker (max 2), then escalate tier, then handle inline

### Negative Rules (What NOT To Do)

- ❌ Do NOT execute subtasks yourself. Delegate.
- ❌ Do NOT give workers vague briefs ("research X"). Use the structured brief template.
- ❌ Do NOT accept verbose worker returns. Require summary + artifact_ref.
- ❌ Do NOT let workers write to shared state in parallel. Single-thread writes or use worktree isolation.
- ❌ Do NOT assume workers share context. They don't. Park shared info on filesystem.
- ❌ Do NOT exceed the fan-out cap.

### When NOT to Delegate

Keep work in the primary context when:
- Shared history is load-bearing (L1)
- The task writes shared state (L2)
- The spec cannot be frozen (ambiguity must be resolved first)
- Total information fits comfortably in one context window
- The task is simple and delegation overhead isn't justified

---

## Harness-Specific Insertion Points

### opencode (AGENTS.md)
```markdown
## Delegation
{{ORCHESTRATOR_INSTRUCTIONS_BLOCK}}
```

### Claude Code (CLAUDE.md)
```markdown
## Delegation
{{ORCHESTRATOR_INSTRUCTIONS_BLOCK}}
```

### Codex (AGENTS.md)
```markdown
## Delegation
{{ORCHESTRATOR_INSTRUCTIONS_BLOCK}}
```

### Gemini CLI (GEMINI.md)
```markdown
## Delegation
{{ORCHESTRATOR_INSTRUCTIONS_BLOCK}}
```

### Cursor (.cursor/rules/delegation.mdc)
```markdown
---
alwaysApply: true
---
{{ORCHESTRATOR_INSTRUCTIONS_BLOCK}}
```