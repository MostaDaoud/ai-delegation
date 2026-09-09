---
name: ai-delegation-wire
description: >
  Generate harness-specific delegation config from a decision contract.
  Renders subagent definitions, orchestrator instructions, routing rules,
  and artifact conventions for opencode, Claude Code, Codex, Gemini CLI,
  or Cursor. Validates no dangling paths. Use when user says "set up
  orchestrator worker", "write the subagent definitions", "configure model
  routing", "make the lead delegate instead of doing it inline", "generate
  delegation config for opencode", "wire up cascade for Claude Code".
---
<!-- fable-discipline-gate:v1 -->

## Pre-flight gate: Fable Discipline (run FIRST)

Before executing any instruction below, adopt the Fable Mindset operating manual at
`C:\Users\mosta\.claude\skills\fable-mindset\SKILL.md`. Apply its Decision Loop
(GROUND -> REASON -> ACT -> OBSERVE -> RE-EVALUATE -> VERIFY -> NARRATE) and its
7 execution rules to every step of this skill. FD runs first; this skill's own
instructions begin only after the discipline is adopted.

# Wire — Generate Delegation Config

Takes a decision contract (from `decide` or user input) → emits working harness config.

---

## Process

### Step 1: Load References

- `../ai-delegation/references/platform-map.md` — neutral principle → native feature per harness
- `../ai-delegation/references/decision-gate.md` — output contract schema
- `../ai-delegation/assets/templates/subagent-definition.md` — worker brief template
- `../ai-delegation/assets/templates/orchestrator-instructions.md` — orchestrator rules block
- `../ai-delegation/assets/templates/routing-rules.md` — P1/P2 routing skeleton

### Step 2: Accept Decision Contract

Input (JSON, file path, or interactive prompts):

```json
{
  "pattern": "P3",
  "mechanism": "subagent" | "relay-cli",
  "model_tiers": {"decomposition": "frontier", "execution": "cheap", "verification": "mid", "synthesis": "frontier"},
  "context_contract": {"child_receives": [...], "child_returns": [...], "fan_out_cap": 5, "artifact_passing": "filesystem", "result_contract": "subagent-summary" | "delegate-relay.result.v1"},
  "verification_gate": {"type": "clean_context_reviewer", "acceptance_criteria": "..."},
  "escalation_trigger": "...",
  "warnings": []
}
```

`mechanism` comes from the decision contract. `"subagent"` (default) emits in-harness worker defs; `"relay-cli"` (P6) emits cross-CLI relay artifacts — see Step 5b and `../ai-delegation/references/cross-cli-relay.md`.

### Step 3: Resolve Harness

User specifies `--harness` (opencode | claude-code | codex | gemini-cli | cursor).
Default: detect from workspace (`.opencode/`, `.claude/`, `.codex/`, `.gemini/`, `.cursor/`).
For `mechanism: "relay-cli"`, the harness governs the orchestrator side only; the worker side is defined by the target CLI (ask for `--target-cli` or take it from lane config).

### Step 4: Resolve Model Tiers → Actual Models

Read local `model-tiers.json` if present:
```json
{"frontier": "opus", "mid": "sonnet", "cheap": "haiku"}
```
Else use `platform-map.md` defaults for the harness.
For `mechanism: "relay-cli"`, the execution tier resolves to the **target CLI's own model** (its pricing applies — feed `delegation_calculator.py` a `p6_worker_tier` price row).

### Step 5: Render Templates

For each worker in the decision:
1. Fill `subagent-definition.md` with context contract fields
2. Write worker file to harness location

For orchestrator:
1. Fill `orchestrator-instructions.md` with pattern-specific rules
2. Write to harness top-level config (AGENTS.md, CLAUDE.md, etc.)

For routing (P1/P2):
1. Fill `routing-rules.md` with tier assignments
2. Write to harness routing location

### Step 5b: Render Relay Artifacts (mechanism: "relay-cli" / P6 only)

1. **Self-contained briefs** → `{artifact_dir}/briefs/{task_id}.md` — the four brief fields (objective, output format, tool guidance, path boundaries) plus gate statement and an explicit no-commit instruction. The brief must assume zero orchestrator chat history.
2. **Lane config** → `.delegation/fleet.yaml` (project) or `~/.delegation/fleet.yaml` (global): `delegate-fleet.v1`-compatible lanes binding work-types to target CLIs with dials. Explicit flags override lane dials; wrong implementer for a lane fails loud.
3. **Dispatch procedure** → `.delegation/dispatch.md`: the review-first loop (write brief → dispatch → poll → review `git diff` → re-run gates → orchestrator commits), referencing `delegate-relay.result.v1` fields. Surface the target CLI's autonomy caveats from `cross-cli-relay.md` as explicit warnings (aider commits by default; grok cannot be prevented from writing; `touchedFiles` is not containment).
4. **Fail-closed binding**: stamp every emitted project config with a `delegation_contract` block: `{contract_hash, approved_by, approved_at}`. A config whose hash does not match an approved contract fails closed — copied or hand-edited project configs must be re-approved before dispatch.

### Step 5c: Render Gate Config (from the decision's `gate` field)

| Decision `gate` | What `wire` emits |
|-----------------|-------------------|
| `none` | Nothing extra; the post-hoc verification gate from the contract covers it |
| `one-line` | The one-liner appended to every brief's brief: **"Report anything you decided that the task did not specify."** |
| `full` | **Enforced read-only worker config** — never prompt-only (AP15): for `mechanism: "subagent"`, a read-only tools *allowlist* in the worker definition; for `mechanism: "relay-cli"`, the target CLI's sandbox/read-only flags plus a **two-pass procedure**: read-only pass → plan + questions → user approval → fresh write pass with the approved plan carrying context (PG2; a session cannot pause and gain permissions). Include a **preflight probe** (trivial read-only dispatch; empty result = sandbox unavailable) and the rule **empty plan = failed run**. If [plan-gate](https://github.com/AgriciDaniel/plan-gate) is installed, reference its planner agent + `audit` instead of re-inventing Lane A. |

### Step 6: Validate

Run `python ../agent-discipline-forge/scripts/validate_skill.py` on emitted config (adapted for harness config schema).
Check: no dangling paths, all referenced files exist, frontmatter valid.

### Step 7: Output

Print the file tree created. Return summary JSON:
```json
{
  "harness": "opencode",
  "files_created": [...],
  "pattern": "P3",
  "verification_artifact": "emitted config passes validate_skill.py"
}
```

---

## Harness Output Locations

| Harness | Orchestrator | Workers | Routing | Top-Level Config |
|---------|--------------|---------|---------|------------------|
| opencode | `.opencode/skill/ai-delegation-orchestrator/SKILL.md` | `.opencode/skill/ai-delegation-worker-*/SKILL.md` | `.opencode/routing/rules.yaml` | `AGENTS.md` |
| Claude Code | `.claude/agents/ai-delegation-orchestrator.md` | `.claude/agents/ai-delegation-worker-*.md` | `.claude/routing/rules.yaml` | `CLAUDE.md` |
| Codex | `.codex/agents/ai-delegation-orchestrator.json` | `.codex/agents/ai-delegation-worker-*.json` | `.codex/routing.json` | `AGENTS.md` |
| Gemini CLI | `.gemini/agents/ai-delegation-orchestrator.json` | `.gemini/agents/ai-delegation-worker-*.json` | `.gemini/routing.json` | `GEMINI.md` |
| Cursor | `.cursor/agents/ai-delegation-orchestrator.json` | `.cursor/agents/ai-delegation-worker-*.json` | `.cursor/routing.json` | `.cursor/rules/delegation.mdc` |

---

## Output Format

Returns file tree + verification status. On error, returns specific fix (D3).

---

## Discipline Gates

- **D2**: Emits only config; logic stays in templates + references
- **D4**: Fan-out caps, verification gates → hook examples in emitted config
- **D8**: Neutral logic; vendor syntax only via `platform-map.md`
- **E1**: Reads target harness config first (ground before mutate)
- **E2**: Runs `validate_skill.py` on emitted config (real check after edit)