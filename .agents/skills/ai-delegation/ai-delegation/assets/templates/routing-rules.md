# Routing Rules Template

This defines the routing logic for P1 (Router) and P2 (Cascade) patterns. For P3/P4/P5, the orchestrator handles dynamic routing.

---

## P1 Router — Rule-Based + Classifier

### Rule-Based Pass (Fast Path, <1ms)

Routes obvious cases before any classifier runs.

```yaml
rules:
  - name: "short-extraction"
    condition: "task_type == 'extract' && token_estimate < 500"
    tier: "cheap"
    model: "{{CHEAP_MODEL}}"

  - name: "classification-binary"
    condition: "task_type == 'classify' && num_classes <= 5"
    tier: "cheap"
    model: "{{CHEAP_MODEL}}"

  - name: "short-summary"
    condition: "task_type == 'summarize' && input_tokens < 2000"
    tier: "cheap"
    model: "{{CHEAP_MODEL}}"

  - name: "common-translation"
    condition: "task_type == 'translate' && language_pair in [EN-ES, EN-FR, EN-DE, EN-PT, EN-IT, EN-JA, EN-KO, EN-ZH]"
    tier: "cheap"
    model: "{{CHEAP_MODEL}}"

  - name: "code-boilerplate"
    condition: "task_type == 'code' && complexity == 'boilerplate'"
    tier: "mid"
    model: "{{MID_MODEL}}"

  - name: "vision-required"
    condition: "requires_vision == true"
    tier: "frontier"
    model: "{{FRONTIER_MODEL}}"

  - name: "ambiguity-detected"
    condition: "ambiguity_score > 0.7"
    tier: "frontier"
    model: "{{FRONTIER_MODEL}}"
```

### Classifier Pass (Ambiguous Middle, ~5–100ms)

For requests not caught by rules. Train a lightweight classifier (BERT / embedding / matrix-factorization) on your eval set.

```yaml
classifier:
  type: "embedding"  # or "bert", "matrix-factorization"
  model: "{{CLASSIFIER_MODEL}}"  # e.g., gte-qwen2-7B-instruct
  threshold: 0.5  # win-rate threshold for strong model
  fallback_tier: "mid"
```

**Training data:** Your eval set (50–500 cases) with labels: `tier_needed` (cheap/mid/frontier).

### Default Fallback

```yaml
default:
  tier: "mid"
  model: "{{MID_MODEL}}"
```

---

## P2 Cascade — Cheap-First → Verify → Escalate

### Cheap Model Answer

```yaml
cheap_model:
  tier: "cheap"
  model: "{{CHEAP_MODEL}}"
  max_tokens: 4000
```

### Verification Gate (Choose One)

#### Option A: Confidence Self-Rating (Math/QA)
```yaml
verifier:
  type: "confidence_self_rating"
  prompt: |
    Rate your confidence in the above answer on a 0–1 scale.
    Return ONLY a JSON: {"confidence": 0.0-1.0, "reasoning": "..."}
  escalate_threshold: 0.7
```

#### Option B: Clean-Context Reviewer (Code/General)
```yaml
verifier:
  type: "clean_context_reviewer"
  reviewer_tier: "mid"
  reviewer_model: "{{MID_MODEL}}"
  prompt: |
    Review the answer for correctness, completeness, and adherence to instructions.
    Return ONLY JSON: {"accept": true/false, "issues": [...], "escalate": true/false}
```

#### Option C: Deterministic Check (Structured Output)
```yaml
verifier:
  type: "deterministic_check"
  checks:
    - "json_schema_valid"
    - "required_fields_present"
    - "no_hallucinated_apis"
  escalate_on_any_fail: true
```

### Escalation

```yaml
escalation:
  tier: "frontier"
  model: "{{FRONTIER_MODEL}}"
  max_escalation_rate: 0.30  # Alert if exceeded
```

### Acceptance Rate Target

```yaml
targets:
  cheap_acceptance_rate: 0.70  # 70% of requests should stop at cheap tier
  quality_floor: 0.95  # vs frontier baseline
```

---

## P3 Orchestrator-Worker — Dynamic Routing (Orchestrator Decides)

The orchestrator's prompt contains the effort-scaling rules (see `orchestrator-instructions.md`). No static routing rules needed.

---

## P4 Advisor — Capability Router (Cross-Frontier Only)

```yaml
advisor_routing:
  # Only valid when BOTH primary and advisor are frontier-tier
  capability_map:
    debugging: "model_a"
    visual_reasoning: "model_b"
    test_writing: "model_c"
    architectural_review: "model_a"
  default: "model_a"
  # Primary asks: "What should I do?" — Advisor decides what's interesting
```

---

## P5 Plan-Then-Execute — Static (Planner → Executor)

```yaml
plan_then_execute:
  planner:
    tier: "frontier"
    model: "{{FRONTIER_MODEL}}"
    output: "frozen_spec"  # written to artifacts/spec/
  executor:
    tier: "cheap"  # or "mid" for code
    model: "{{CHEAP_MODEL}}"  # or "{{MID_MODEL}}"
    persistent: true  # revisions hit cached context
```

---

## P6 Cross-CLI Relay — Lane Config (work-type → implementer CLI)

Lanes are P1 routing at the process level. Emitted by `wire` as `.delegation/fleet.yaml` (`delegate-fleet.v1`-compatible shape).

```yaml
lanes:
  - name: feature
    implementer: codex
    dials: {model: "{{TARGET_CLI_MODEL}}", sandbox: workspace-write}
  - name: tests
    implementer: cursor-agent
    dials: {read_only: false}
  - name: ui
    implementer: opencode
    dials: {model: "{{TARGET_CLI_MODEL_2}}"}
```

Lane rules (DS3):
- Explicit dispatch flags **override** lane dials.
- The wrong implementer for a lane **fails loud**.
- Project lane config is **content-bound** to the approved decision contract (`delegation_contract.block` with `contract_hash`); a copied or hand-edited config **fails closed** until re-approved.

Every P6 dispatch follows the review-first loop in `cross-cli-relay.md`: brief → dispatch → poll → review `git diff` → re-run gates → orchestrator commits. The relay never commits (AP13); `touchedFiles` is a review aid, not containment (AP14).

---

## Harness-Specific Notes

### opencode
- Save as `.opencode/routing/rules.yaml`
- Skills can read via `Read` tool
- Hooks can enforce max fan-out

### Claude Code
- Save as `.claude/routing/rules.yaml`
- CLAUDE.md references it: "Follow routing rules in .claude/routing/rules.yaml"

### Codex / Gemini CLI / Cursor
- Save as `.codex/routing.json`, `.gemini/routing.json`, `.cursor/routing.json`
- AGENTS.md / GEMINI.md / rules reference it