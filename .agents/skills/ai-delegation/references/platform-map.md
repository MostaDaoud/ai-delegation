# Platform Mapping — Neutral Principle → Native Feature

The skill's logic is harness-neutral. This file maps each principle to the native feature in each supported harness. The `wire` sub-skill uses this to emit harness-specific config.

---

## Supported Harnesses

| Harness | Config Entry Point | Subagent Mechanism | Model Selection | Routing/Automation |
|---------|-------------------|-------------------|-----------------|-------------------|
| **opencode** | `.opencode/skill/` + `AGENTS.md` | `Task` tool / subagents | Per-agent `model` in skill frontmatter | Skill routing + hooks |
| **Claude Code** | `.claude/agents/` + `CLAUDE.md` | `Task` tool / subagents | Per-subagent `model` param | CLAUDE.md instructions + hooks |
| **Codex (OpenAI)** | `.codex/agents/` + `AGENTS.md` | `subagent` / `handoff` | Per-agent config | AGENTS.md + function calling |
| **Gemini CLI** | `.gemini/agents/` + `GEMINI.md` | `agent` / `delegate` | Per-agent config | GEMINI.md + tools |
| **Cursor** | `.cursor/rules/` + agents | `@agent` / `@agent run` | Per-agent config | Rules + agent definitions |

---

## Principle → Native Feature Mapping

### Subagent Creation & Context Isolation

| Principle | opencode | Claude Code | Codex | Gemini CLI | Cursor |
|-----------|----------|-------------|-------|------------|--------|
| Spawn isolated subagent | `Task` tool in skill | `Task` tool with `subagent_type` | `subagent` tool | `delegate` tool | `@agent run` |
| Per-subagent model | `model` in skill frontmatter | `model` param in Task | `model` in agent config | `model` in agent config | `model` in agent config |
| Subagent context isolation | Automatic (separate conversation) | Automatic (separate context window) | Automatic | Automatic | Automatic |
| Subagent returns summary only | Skill instruction | Skill instruction | Agent instruction | Agent instruction | Agent instruction |

### Delegation Patterns

| Pattern | opencode | Claude Code | Codex | Gemini CLI | Cursor |
|---------|----------|-------------|-------|------------|--------|
| **P1 Router** | Skill with routing logic + `model` per sub-skill | CLAUDE.md routing block + Task with model | AGENTS.md router agent + subagent model | GEMINI.md router + agent model | Rules router + agent model |
| **P2 Cascade** | Skill with verifier sub-skill + escalation | CLAUDE.md cascade logic + Task escalation | AGENTS.md cascade + subagent | GEMINI.md cascade + agent | Rules cascade + agent |
| **P3 Orchestrator-Worker** | Orchestrator skill + worker sub-skills | Lead agent + Task subagents | Main agent + subagents | Main agent + delegate | Main agent + @agent |
| **P4 Advisor** | Primary skill + advisor sub-skill | Primary + Task to advisor | Primary + subagent | Primary + delegate | Primary + @agent |
| **P5 Plan-Then-Execute** | Planner skill + persistent executor | Lead + persistent Task session | Main + persistent subagent | Main + persistent delegate | Main + persistent @agent |

### Model Selection / Tier Mapping

| Tier | opencode | Claude Code | Codex | Gemini CLI | Cursor |
|------|----------|-------------|-------|------------|--------|
| frontier | `model: opus` / `fable` | `model: "opus"` / `"fable-5"` | `model: "gpt-5"` / `"o1-pro"` | `model: "gemini-2.5-pro"` | `model: "gpt-5"` |
| mid | `model: sonnet` | `model: "sonnet"` | `model: "gpt-4o"` | `model: "gemini-2.5-flash"` | `model: "gpt-4o"` |
| cheap | `model: haiku` | `model: "haiku"` | `model: "gpt-4o-mini"` | `model: "gemini-2.5-flash-lite"` | `model: "gpt-4o-mini"` |

> **The `wire` sub-skill reads your local `model-tiers.json` (if present) to override these defaults.**

### Artifact Passing (Filesystem Convention)

| Principle | opencode | Claude Code | Codex | Gemini CLI | Cursor |
|-----------|----------|-------------|-------|------------|--------|
| Worker writes artifacts | Skill writes to `.opencode/artifacts/{worker_id}/` | Task writes to `.claude/artifacts/{worker_id}/` | Subagent writes to `.codex/artifacts/{worker_id}/` | Delegate writes to `.gemini/artifacts/{worker_id}/` | Agent writes to `.cursor/artifacts/{worker_id}/` |
| Orchestrator reads artifacts | Read tool | Read tool | Read tool | Read tool | Read tool |
| Lightweight ref returned | `{artifact_ref, summary}` | Same | Same | Same | Same |

### Fan-Out Cap & Effort Scaling

| Principle | opencode | Claude Code | Codex | Gemini CLI | Cursor |
|-----------|----------|-------------|-------|------------|--------|
| Fan-out cap | Orchestrator skill instruction: `max_workers: 5` | CLAUDE.md: "Never spawn more than 5 subagents" | AGENTS.md: max 5 subagents | GEMINI.md: max 5 delegates | Rules: max 5 agents |
| Effort scaling | Skill: simple=1/3-10, complex=>10 | CLAUDE.md rules | AGENTS.md rules | GEMINI.md rules | Rules |

### Verification Gate

| Principle | opencode | Claude Code | Codex | Gemini CLI | Cursor |
|-----------|----------|-------------|-------|------------|--------|
| Clean-context reviewer | Separate skill with `context: fork` | Separate Task with fresh context | Separate subagent | Separate delegate | Separate @agent |
| Deterministic check | Script in `scripts/` | Script in `scripts/` | Script | Script | Script |

### Hooks / Enforcement (D4)

| Principle | opencode | Claude Code | Codex | Gemini CLI | Cursor |
|-----------|----------|-------------|-------|------------|--------|
| Pre-tool validation | Skill `hooks:` frontmatter | `.claude/hooks/` | AGENTS.md hooks | GEMINI.md hooks | Cursor rules |
| Fan-out cap enforcement | Hook on Task spawn | Hook on Task spawn | Hook on subagent | Hook on delegate | Rule on @agent run |

---

## P6 Mechanism — Cross-CLI Relay (mechanism: "relay-cli")

When `decide` outputs `mechanism: "relay-cli"`, `wire` emits relay-ready artifacts instead of in-harness subagent defs. This is harness-independent (the worker runs in a *different* process), so the mapping is by target CLI, not by orchestrating harness.

| Emitted artifact | Location | Contents |
|------------------|----------|----------|
| Self-contained brief | `{artifact_dir}/briefs/{task_id}.md` | Objective, output format, tool guidance, path boundaries, gate statement, no-commit instruction |
| Lane config | `.delegation/fleet.yaml` (project) or `~/.delegation/fleet.yaml` (global) | `delegate-fleet.v1`-compatible lanes: work-type → implementer CLI + dials |
| Dispatch procedure | `.delegation/dispatch.md` | The review-first loop: write brief → dispatch → poll → review `git diff` → re-run gates → orchestrator commits |
| Result contract | referenced in dispatch.md | `delegate-relay.result.v1`: status, exitCode, signal, report, touchedFiles, sessionId |

**Fail-closed binding (DS3):** every emitted project config carries a `delegation_contract` block containing the decision-contract hash and approval reference. A copied or hand-edited config whose hash does not match an approved contract **fails closed** — audit flags it and `wire` refuses to dispatch against it until re-approved.

**Dispatch execution:** this skill decides and wires; it does not ship relay scripts. If [delegate-skills](https://github.com/amElnagdy/delegate-skills) is installed, its per-CLI `*-delegate` skills are the reference relays. If not, the orchestrator uses the target CLI's documented headless mode with the emitted brief + procedure. Either way the four invariants in `cross-cli-relay.md` hold.

---

## `wire` Sub-Skill Output Per Harness

When the user runs `/ai-delegation wire --harness <name>`, the sub-skill emits:

### opencode
```
.opencode/
  skill/
    ai-delegation-orchestrator/
      SKILL.md           # orchestrator with routing logic
      hooks/             # fan-out cap, verification gate
    ai-delegation-worker-{type}/
      SKILL.md           # worker with model: cheap
  AGENTS.md              # top-level delegation instruction block
```

### Claude Code
```
.claude/
  agents/
    ai-delegation-orchestrator.md   # lead agent
    ai-delegation-worker-{type}.md  # workers
  CLAUDE.md                          # delegation rules + effort scaling
```

### Codex
```
.codex/
  agents/
    ai-delegation-orchestrator.json
    ai-delegation-worker-{type}.json
  AGENTS.md
```

### Gemini CLI
```
.gemini/
  agents/
    ai-delegation-orchestrator.json
    ai-delegation-worker-{type}.json
  GEMINI.md
```

### Cursor
```
.cursor/
  rules/
    ai-delegation-orchestrator.mdc
    ai-delegation-worker-{type}.mdc
  agents/
    ai-delegation-orchestrator.json
    ai-delegation-worker-{type}.json
```

---

## How `wire` Uses This

1. Reads the `decision_contract` from `decide` output (or user input)
2. Looks up harness in this file
3. Renders `assets/templates/` with the contract values
4. Writes the harness-specific file tree
5. Validates no dangling paths