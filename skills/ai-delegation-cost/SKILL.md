---
name: ai-delegation-cost
description: >
  Model delegation economics across P1–P5 patterns. Takes your model prices,
  traffic mix, task distribution, escalation rate, cache-hit rate, and fan-out.
  Outputs cost per 1k tasks for each strategy, break-even escalation rate,
  and quality-floor warnings. Use when user says "is delegation worth it",
  "what will this cost", "break-even escalation rate", "cut my API bill",
  "cheaper model routing math", "P1 vs P2 vs P3 cost", "delegation calculator",
  "RouteLLM savings", "FrugalGPT cascade cost".
---

# Cost — Delegation Economics Calculator

Runs `../ai-delegation/scripts/delegation_calculator.py` with your config. Compares all five
patterns + always-frontier baseline. Flags when cascade costs MORE than
frontier, when fan-out risks overflow, when cheap share risks regression.

---

## Process

### Step 1: Load Config

Accept `--config` path (JSON). Schema:

```json
{
  "model_prices": {
    "frontier": {"name": "opus", "input_per_m": 75.0, "output_per_m": 300.0},
    "mid": {"name": "sonnet", "input_per_m": 10.0, "output_per_m": 40.0},
    "cheap": {"name": "haiku", "input_per_m": 0.50, "output_per_m": 2.00}
  },
  "traffic_per_day": 1000,
  "task_distribution": [
    {"name": "routine", "share": 0.70, "avg_input_tokens": 2000, "avg_output_tokens": 500, "requires_frontier": false},
    {"name": "code", "share": 0.20, "avg_input_tokens": 4000, "avg_output_tokens": 1500, "requires_frontier": false},
    {"name": "complex", "share": 0.10, "avg_input_tokens": 8000, "avg_output_tokens": 3000, "requires_frontier": true}
  ],
  "escalation_rate": 0.15,
  "cache_hit_rate": 0.80,
  "fan_out": 4,
  "cheap_acceptance_rate": 0.70,
  "quality_floor": 0.95
}
```

Defaults in script if omitted (clearly marked as anchors, not predictions).

### Step 2: Run Calculator

Executes `../ai-delegation/scripts/delegation_calculator.py` which computes:

| Strategy | Model | Key Formula |
|----------|-------|-------------|
| Always-Frontier | 100% frontier | frontier_price × tokens |
| P1 Router | Classify → one model | tier_per_task × tier_price |
| P2 Cascade | Cheap → verify → escalate | cheap + verifier + escalation_rate × frontier |
| P3 Orchestrator-Worker | Frontier plans, cheap workers | frontier(20%) + cheap(80%) × 15× multiplier |
| P5 Plan-Then-Execute | Frontier spec, cheap executor | frontier(15%) + cheap(85%) × cache_hit_factor |

**Token multipliers from Anthropic (A2):**
- Single agent ≈ 4× chat tokens
- Multi-agent ≈ 15× chat tokens

### Step 3: Output Comparison

Returns JSON + markdown table:

```json
{
  "strategies": {
    "always_frontier": {"cost_per_1k": 125.00, "quality_vs_frontier": 1.0, "avg_tokens_per_task": 45000},
    "p1_router": {"cost_per_1k": 32.50, "quality_vs_frontier": 0.95, "avg_tokens_per_task": 45000},
    "p2_cascade": {"cost_per_1k": 28.90, "quality_vs_frontier": 0.95, "break_even_escalation_rate": 0.34},
    "p3_orchestrator_worker": {"cost_per_1k": 89.00, "quality_vs_frontier": 0.95, "token_multiplier_vs_chat": 15.0},
    "p5_plan_then_execute": {"cost_per_1k": 24.50, "quality_vs_frontier": 0.98, "assumptions": "cache_hit=0.8"}
  },
  "recommendation": {"strategy": "p5_plan_then_execute", "reason": "Lowest cost ($24.50/1k) while meeting quality floor (0.95)"},
  "warnings": [
    "P2 cascade escalation rate (15%) below break-even (34%) — viable",
    "P3 fan-out (4) within safe range (<10)"
  ],
  "notes": ["Run your own eval with 50-500 cases before committing"]
}
```

### Step 4: Quality-Floor Warning

If `quality_vs_frontier < quality_floor` for a strategy, it's excluded from recommendation and flagged.

---

## Output Format

JSON to stdout (or `--output` file). Includes:
- `strategies`: all 5 + baseline
- `recommendation`: cheapest viable or null
- `warnings`: break-even exceeded, fan-out >10, cheap share >85%
- `notes`: provenance reminders (A2, R1, P5)

---

## Discipline Gates

- **D1**: Names verification artifact — the cost table itself; user verifies by running their own eval
- **D5**: Parameterized by config file, not hardcoded narrative
- **E5**: Batch independent work — computes all 5 strategies in one pass
- **E7**: Honest narration — every output includes assumptions, warnings, and "run your own eval" note