---
name: ai-delegation
description: >
  Decide when and how to delegate work across AI agents and model tiers.
  Runs an 8-question gate over three failure laws, recommends one of
  six delegation patterns (Router, Cascade, Orchestrator-Worker, Advisor,
  Plan-Then-Execute, Cross-CLI Relay), assigns model tiers per role, and wires
  the config for your harness (opencode, Claude Code, Codex, Gemini CLI,
  Cursor), including cross-CLI dispatch via a review-first relay. Includes a
  P1-P6 cost calculator, AP1-AP14 anti-pattern auditor, fail-closed lane
  configs, and a confidence-dated evidence base. Use when user says "should I
  delegate this", "which model for this task", "orchestrator worker",
  "subagent", "cut my API bill", "cheaper model", "context pollution",
  "route requests", "cascade cheap to strong", "delegate to codex/cursor",
  "fleet lanes", "audit my subagents", "delegation anti-patterns". Do NOT use
  for prompt engineering, RAG tuning, fine-tuning, human team delegation, or
  general "make my agent better" without a   delegation/routing/cost component.
metadata:
  author: Mostafa Daoud
  version: 1.1.0
  credits: >-
    Based partly on https://github.com/amElnagdy/delegate-skills (P6 Cross-CLI
    Relay pattern, MIT) and https://github.com/AgriciDaniel/skill-forge (skill
    architecture and build pipeline, MIT).
---

# AI Delegation — Decide, Wire, Cost, Audit

Route work across agents and model tiers without guesswork. This skill encodes the
five proven delegation patterns, three failure laws, and a decision gate that
outputs a complete delegation contract — or tells you **don't delegate**.

---

## Quick Reference

| Command | Routes to | Purpose |
|---------|-----------|---------|
| `/ai-delegation` | Interactive mode | Walk the 8-question gate, then route |
| `/ai-delegation decide` | `../ai-delegation-decide/` | Should I delegate? Pattern + tiers + context contract |
| `/ai-delegation wire` | `../ai-delegation-wire/` | Generate harness-specific config |
| `/ai-delegation cost` | `../ai-delegation-cost/` | Run the economics calculator |
| `/ai-delegation audit` | `../ai-delegation-audit/` | Audit existing setup for 14 anti-patterns |

---

## Orchestration Logic

When user invokes `/ai-delegation`:

1. **Detect intent** — parse the query for delegation/routing/cost/audit keywords
2. **Route** to the appropriate sub-skill (or walk the gate interactively)
3. **Execute** the sub-skill workflow
4. **Return** structured output (decision contract, config files, cost table, or audit findings)

---

## Reference Files

Load on-demand as needed:

- `references/evidence.md` — Source table with confidence + `refresh_due` per claim
- `references/patterns.md` — Six patterns: shape, wins, losses, anchor, when each wins
- `references/decision-gate.md` — 8 questions, decision tree, output contract, hard rules
- `references/cross-cli-relay.md` — P6 mechanics: review-first loop, four invariants, result contract, per-CLI autonomy caveats, fleet lanes
- `references/model-tier-matrix.md` — Role × capability → tier defaults
- `references/anti-patterns.md` — 14 named failure modes (AP1–AP14) with detection + fix
- `references/platform-map.md` — Neutral principle → native feature per harness + P6 relay artifacts

---

## Sub-Skills

1. **ai-delegation-decide** — Run the 8-question gate; emit delegation decision contract
2. **ai-delegation-wire** — Render harness-specific config from a decision contract
3. **ai-delegation-cost** — Model economics across P1–P5; break-even + quality-floor warnings
4. **ai-delegation-audit** — Static scan for AP1–AP12; severity-ranked findings + fixes

---

## Discipline Gates (D1–D10 + E1–E7)

This skill enforces the agent-discipline-forge gates:

- **D1 Plan-first**: Every mutating sub-skill (`wire`) names its verification artifact (rendered config passes `validate_skill.py`)
- **D2 Progressive disclosure**: SKILL.md < 500 lines; detail in `references/` and `scripts/`
- **D3 Trigger-grade description**: WHAT + WHEN + ≥5 triggers + negative triggers (see frontmatter)
- **D4 Enforcement split**: Fan-out caps, "must verify" rules → hook examples in `platform-map.md`
- **D5 Procedure-pack shape**: Sub-skills are parameterized workflows, not hardcoded narratives
- **D6 Context hygiene**: No inline reference material; all loaded on-demand from `references/`
- **D7 Delegation scoping**: **Primary gate** — every decision emits `context_contract` (child receives / returns / fan-out cap / failure behavior)
- **D8 Model/harness neutrality**: Neutral phrasing in logic; vendor syntax only in `platform-map.md`
- **D9 Packagability**: Team-targeted; install path tested via `discipline-forge publish`
- **D10 Eval-worthiness**: Ships 10 should-trigger / 10 should-not-trigger cases (see Eval section)

**Execution gates (E1–E7)** carried in sub-skill instructions:
- E1 Ground before mutate — `wire` reads target harness config first
- E2 Real check after edit — `wire` runs `validate_skill.py` on emitted config
- E3 Diagnose before retry — `audit` reports specific fix per finding
- E4 Read before edit — `decide` reads `references/` before emitting contract
- E5 Batch independent work — `cost` computes all 5 strategies in one pass
- E6 Calibrated effort — `decide` MUST be able to output `pattern: none` (don't delegate)
- E7 Honest narration — All outputs include warnings, assumptions, and provenance

---

## Eval Set

### Should-Trigger (10)

| Query | Expected Route |
|-------|----------------|
| "should I delegate this research to subagents" | `decide` → P3 or none |
| "which model should the worker use for code generation" | `decide` → mid tier |
| "my orchestrator keeps running out of context" | `decide` → L3 warning + fan-out cap |
| "will delegating to Haiku-class actually save money" | `cost` → cascade vs router comparison |
| "write me subagent definitions for opencode" | `wire` → opencode config |
| "my two subagents produce conflicting code" | `audit` → AP5 finding |
| "set up a cheap-first cascade with escalation" | `wire` → P2 cascade config |
| "is orchestrator-worker worth 15x tokens here" | `decide` → P3 only if quality binding |
| "audit my subagent config for anti-patterns" | `audit` → full AP1–AP12 scan |
| "cut my agent API bill without losing quality" | `cost` → P1/P2 recommendation |

### Should-NOT-Trigger (10)

| Query | Why Not |
|-------|---------|
| "write a better prompt for this" | Prompt engineering, not delegation |
| "tune my RAG chunking" | Retrieval, not agent/model routing |
| "fine-tune a model on my data" | Training, not delegation |
| "how do I delegate work to my team" | Human delegation |
| "orchestrate my Kubernetes deployments" | Infrastructure, not AI agents |
| "explain transformers" | Knowledge, not decision |
| "fix this failing test" | Debugging, not delegation |
| "which LLM is smartest overall" | Model comparison, not routing |
| "set up CI" | CI/CD, not delegation |
| "summarize this document" | Single task, no delegation component |

---

## Scripts

- `scripts/delegation_calculator.py` — Cost model across P1–P5 + break-even
- `scripts/audit_delegation.py` — Static scan for AP1–AP12

## Assets

- `assets/templates/subagent-definition.md` — Worker brief template (all 4 fields required)
- `assets/templates/orchestrator-instructions.md` — Orchestrator delegation rules block
- `assets/templates/routing-rules.md` — P1/P2 routing rules skeleton

---

## Negative Triggers

Do NOT activate for: prompt engineering, RAG/retrieval tuning, model fine-tuning, human team delegation, Kubernetes/service orchestration, general "make my agent better" without delegation/routing/cost component, simple code formatting, syntax questions, general-purpose data analysis.