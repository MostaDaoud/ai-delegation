#!/usr/bin/env python3
"""
Purpose: Model delegation economics across P1-P6 patterns.
Input: JSON config with model prices, traffic mix, task distribution, escalation rate, cache-hit rate, fan-out.
Output: JSON cost comparison per 1k tasks + break-even analysis + quality-floor warning.
Usage: python scripts/delegation_calculator.py --config config.json [--output out.json]
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class ModelPrice:
    name: str
    tier: str  # frontier, mid, cheap
    input_per_m: float
    output_per_m: float


@dataclass
class TaskTypeDist:
    name: str
    share: float  # 0-1, sums to 1
    avg_input_tokens: int
    avg_output_tokens: int
    requires_frontier: bool  # some task types (vision, complex reasoning) can't be delegated


@dataclass
class Config:
    model_prices: Dict[str, ModelPrice]  # key = tier
    traffic_per_day: int
    task_distribution: List[TaskTypeDist]
    escalation_rate: float  # for P2: fraction of cheap calls that escalate
    cache_hit_rate: float  # for P5: cached context fraction
    fan_out: int  # for P3: avg workers per task
    cheap_acceptance_rate: float  # for P2: target acceptance rate
    quality_floor: float  # minimum quality vs frontier (0-1)
    p6_worker_tier: str  # for P6: key into model_prices for the target CLI's model
    p6_local_endpoint: bool  # for P6: target CLI runs a local/self-hosted endpoint (~0 marginal)


# Default price table (mid-2026 reference; user should override)
DEFAULT_PRICES = {
    "frontier": ModelPrice("frontier", "frontier", 75.0, 300.0),
    "mid": ModelPrice("mid", "mid", 10.0, 40.0),
    "cheap": ModelPrice("cheap", "cheap", 0.50, 2.00),
}

# Token multipliers from Anthropic research (A2)
AGENT_TOKEN_MULTIPLIER = 4.0      # single agent vs chat
MULTI_AGENT_TOKEN_MULTIPLIER = 15.0  # multi-agent vs chat


def load_config(path: str) -> Config:
    with open(path) as f:
        raw = json.load(f)

    prices = {}
    for tier, p in raw.get("model_prices", {}).items():
        prices[tier] = ModelPrice(p["name"], tier, p["input_per_m"], p["output_per_m"])
    if not prices:
        prices = DEFAULT_PRICES

    task_dist = []
    for t in raw.get("task_distribution", []):
        task_dist.append(TaskTypeDist(
            t["name"], t["share"], t["avg_input_tokens"], t["avg_output_tokens"],
            t.get("requires_frontier", False)
        ))
    if not task_dist:
        # Default: 70% routine, 20% code, 10% complex
        task_dist = [
            TaskTypeDist("routine", 0.70, 2000, 500, False),
            TaskTypeDist("code", 0.20, 4000, 1500, False),
            TaskTypeDist("complex", 0.10, 8000, 3000, True),
        ]

    return Config(
        model_prices=prices,
        traffic_per_day=raw.get("traffic_per_day", 1000),
        task_distribution=task_dist,
        escalation_rate=raw.get("escalation_rate", 0.15),
        cache_hit_rate=raw.get("cache_hit_rate", 0.80),
        fan_out=raw.get("fan_out", 4),
        cheap_acceptance_rate=raw.get("cheap_acceptance_rate", 0.70),
        quality_floor=raw.get("quality_floor", 0.95),
        p6_worker_tier=raw.get("p6_worker_tier", "mid"),
        p6_local_endpoint=raw.get("p6_local_endpoint", False),
    )


def cost_per_million(input_per_m: float, output_per_m: float, in_tokens: int, out_tokens: int) -> float:
    return (input_per_m * in_tokens / 1_000_000) + (output_per_m * out_tokens / 1_000_000)


def compute_always_frontier(cfg: Config) -> Dict[str, Any]:
    """Strategy: everything on frontier model."""
    frontier = cfg.model_prices["frontier"]
    total_cost = 0.0
    total_tokens = 0
    for t in cfg.task_distribution:
        if t.requires_frontier:
            c = cost_per_million(frontier.input_per_m, frontier.output_per_m,
                                 t.avg_input_tokens, t.avg_output_tokens)
            total_cost += c * t.share
            total_tokens += (t.avg_input_tokens + t.avg_output_tokens) * t.share
        else:
            c = cost_per_million(frontier.input_per_m, frontier.output_per_m,
                                 t.avg_input_tokens, t.avg_output_tokens)
            total_cost += c * t.share
            total_tokens += (t.avg_input_tokens + t.avg_output_tokens) * t.share
    return {
        "strategy": "always_frontier",
        "cost_per_task": total_cost,
        "cost_per_1k": total_cost * 1000,
        "avg_tokens_per_task": total_tokens,
        "quality_vs_frontier": 1.0,
    }


def compute_p1_router(cfg: Config) -> Dict[str, Any]:
    """Strategy: P1 Router — classify each request, send to one model."""
    # Simplified: routine→cheap, code→mid, complex→frontier
    # In reality, classifier accuracy determines the split.
    # We model it as: fraction f goes to cheap, m to mid, r to frontier
    # with quality degradation on misrouted requests.
    total_cost = 0.0
    total_tokens = 0
    for t in cfg.task_distribution:
        if t.requires_frontier:
            tier = "frontier"
        elif t.name == "code":
            tier = "mid"
        else:
            tier = "cheap"
        p = cfg.model_prices[tier]
        c = cost_per_million(p.input_per_m, p.output_per_m,
                             t.avg_input_tokens, t.avg_output_tokens)
        total_cost += c * t.share
        total_tokens += (t.avg_input_tokens + t.avg_output_tokens) * t.share

    # Router overhead: ~5ms embeddings + classifier = negligible vs LLM latency
    # Quality: assume classifier achieves target (depends on eval)
    return {
        "strategy": "p1_router",
        "cost_per_task": total_cost,
        "cost_per_1k": total_cost * 1000,
        "avg_tokens_per_task": total_tokens,
        "quality_vs_frontier": cfg.quality_floor,  # assumes eval gate passes
        "assumptions": "Perfect classifier; real quality depends on calibration eval"
    }


def compute_p2_cascade(cfg: Config) -> Dict[str, Any]:
    """Strategy: P2 Cascade — cheap answers, verify, escalate on fail."""
    cheap = cfg.model_prices["cheap"]
    frontier = cfg.model_prices["frontier"]
    total_cost = 0.0
    total_tokens = 0
    escalated = 0

    for t in cfg.task_distribution:
        if t.requires_frontier:
            # Goes straight to frontier
            c = cost_per_million(frontier.input_per_m, frontier.output_per_m,
                                 t.avg_input_tokens, t.avg_output_tokens)
            total_cost += c * t.share
            total_tokens += (t.avg_input_tokens + t.avg_output_tokens) * t.share
            continue

        # Cheap attempt
        c_cheap = cost_per_million(cheap.input_per_m, cheap.output_per_m,
                                    t.avg_input_tokens, t.avg_output_tokens)
        total_cost += c_cheap * t.share
        total_tokens += (t.avg_input_tokens + t.avg_output_tokens) * t.share

        # Verifier cost (mid-tier, small context)
        mid = cfg.model_prices["mid"]
        verifier_in = t.avg_input_tokens + t.avg_output_tokens  # approx
        verifier_out = 200
        c_verify = cost_per_million(mid.input_per_m, mid.output_per_m,
                                     verifier_in, verifier_out)
        total_cost += c_verify * t.share
        total_tokens += (verifier_in + verifier_out) * t.share

        # Escalation
        esc = cfg.escalation_rate
        if esc > 0:
            c_frontier = cost_per_million(frontier.input_per_m, frontier.output_per_m,
                                           t.avg_input_tokens, t.avg_output_tokens)
            total_cost += c_frontier * t.share * esc
            total_tokens += (t.avg_input_tokens + t.avg_output_tokens) * t.share * esc
            escalated += t.share * esc

    return {
        "strategy": "p2_cascade",
        "cost_per_task": total_cost,
        "cost_per_1k": total_cost * 1000,
        "avg_tokens_per_task": total_tokens,
        "quality_vs_frontier": cfg.quality_floor,  # assumes verifier catches failures
        "escalation_rate_actual": escalated,
        "break_even_escalation_rate": compute_break_even_cascade(cfg),
        "assumptions": f"Escalation rate {cfg.escalation_rate}; verifier false-accepts not modeled"
    }


def compute_break_even_cascade(cfg: Config) -> float:
    """At what escalation rate does cascade cost = always-frontier?"""
    # Solve: cost_cascade(esc) = cost_always_frontier
    # cost_cascade = cost_cheap + cost_verify + esc * cost_frontier
    # For each task type
    frontier = cfg.model_prices["frontier"]
    cheap = cfg.model_prices["cheap"]
    mid = cfg.model_prices["mid"]

    cost_always = 0
    for t in cfg.task_distribution:
        cost_always += cost_per_million(frontier.input_per_m, frontier.output_per_m,
                                         t.avg_input_tokens, t.avg_output_tokens) * t.share

    cost_cascade_base = 0  # without escalation
    for t in cfg.task_distribution:
        if t.requires_frontier:
            cost_cascade_base += cost_per_million(frontier.input_per_m, frontier.output_per_m,
                                                   t.avg_input_tokens, t.avg_output_tokens) * t.share
        else:
            cost_cascade_base += cost_per_million(cheap.input_per_m, cheap.output_per_m,
                                                   t.avg_input_tokens, t.avg_output_tokens) * t.share
            # verifier
            verifier_in = t.avg_input_tokens + t.avg_output_tokens
            cost_cascade_base += cost_per_million(mid.input_per_m, mid.output_per_m,
                                                   verifier_in, 200) * t.share

    if cost_cascade_base >= cost_always:
        return 0.0  # never breaks even

    # Extra cost per escalation
    esc_cost_per_unit = 0
    for t in cfg.task_distribution:
        if not t.requires_frontier:
            esc_cost_per_unit += cost_per_million(frontier.input_per_m, frontier.output_per_m,
                                                   t.avg_input_tokens, t.avg_output_tokens) * t.share

    if esc_cost_per_unit == 0:
        return 1.0

    return (cost_always - cost_cascade_base) / esc_cost_per_unit


def compute_p3_orchestrator_worker(cfg: Config) -> Dict[str, Any]:
    """Strategy: P3 Orchestrator-Worker — frontier plans, cheap workers execute in parallel."""
    frontier = cfg.model_prices["frontier"]
    cheap = cfg.model_prices["cheap"]
    mid = cfg.model_prices["mid"]

    # Orchestrator: planning + synthesis (~20% of total tokens per A4/A5)
    # Workers: execution (~80%)
    total_cost = 0.0
    total_tokens = 0

    for t in cfg.task_distribution:
        base_in = t.avg_input_tokens
        base_out = t.avg_output_tokens

        # Orchestrator tokens (planning + synthesis)
        orch_in = int(base_in * 0.3)  # planning sees full context
        orch_out = int(base_out * 0.5)  # synthesis
        total_cost += cost_per_million(frontier.input_per_m, frontier.output_per_m,
                                        orch_in, orch_out) * t.share
        total_tokens += (orch_in + orch_out) * t.share

        # Workers: fan_out workers, each does a slice
        worker_in = int(base_in / cfg.fan_out) * cfg.fan_out  # each gets slice
        worker_out = int(base_out / cfg.fan_out) * cfg.fan_out
        # Multi-agent token multiplier
        worker_tokens_multiplier = MULTI_AGENT_TOKEN_MULTIPLIER / AGENT_TOKEN_MULTIPLIER  # ~3.75x vs single agent
        worker_in_eff = int(worker_in * worker_tokens_multiplier)
        worker_out_eff = int(worker_out * worker_tokens_multiplier)

        if t.requires_frontier:
            # Workers also need frontier for complex tasks
            total_cost += cost_per_million(frontier.input_per_m, frontier.output_per_m,
                                            worker_in_eff, worker_out_eff) * t.share
        else:
            total_cost += cost_per_million(cheap.input_per_m, cheap.output_per_m,
                                            worker_in_eff, worker_out_eff) * t.share
        total_tokens += (worker_in_eff + worker_out_eff) * t.share

        # Verifier (mid-tier)
        verifier_in = int(base_out * 0.5)  # synthesis output
        verifier_out = 300
        total_cost += cost_per_million(mid.input_per_m, mid.output_per_m,
                                        verifier_in, verifier_out) * t.share
        total_tokens += (verifier_in + verifier_out) * t.share

    return {
        "strategy": "p3_orchestrator_worker",
        "cost_per_task": total_cost,
        "cost_per_1k": total_cost * 1000,
        "avg_tokens_per_task": total_tokens,
        "token_multiplier_vs_chat": MULTI_AGENT_TOKEN_MULTIPLIER,
        "quality_vs_frontier": 0.95,  # A1: 90.2% improvement on research; cap at ~95%
        "assumptions": f"Fan-out={cfg.fan_out}; 15× token multiplier from Anthropic A2"
    }


def compute_p5_plan_then_execute(cfg: Config) -> Dict[str, Any]:
    """Strategy: P5 Plan-Then-Execute — frontier freezes spec, cheap executor runs."""
    frontier = cfg.model_prices["frontier"]
    cheap = cfg.model_prices["cheap"]
    mid = cfg.model_prices["mid"]

    total_cost = 0.0
    total_tokens = 0

    for t in cfg.task_distribution:
        if t.requires_frontier:
            # Planner + executor both frontier
            total_cost += cost_per_million(frontier.input_per_m, frontier.output_per_m,
                                            t.avg_input_tokens, t.avg_output_tokens) * t.share
            total_tokens += (t.avg_input_tokens + t.avg_output_tokens) * t.share
            continue

        # Planner (frontier): writes frozen spec (~15% of tokens)
        plan_in = int(t.avg_input_tokens * 0.5)
        plan_out = int(t.avg_output_tokens * 0.3)
        total_cost += cost_per_million(frontier.input_per_m, frontier.output_per_m,
                                        plan_in, plan_out) * t.share
        total_tokens += (plan_in + plan_out) * t.share

        # Executor (cheap): executes spec (~85% of tokens)
        exec_in = int(t.avg_input_tokens * 0.5)  # spec + context
        exec_out = int(t.avg_output_tokens * 0.7)
        # Cache hit: revisions use cached context (~10% cost per P4)
        # Assume 2 revisions per task on average
        revisions = 2
        exec_cost_base = cost_per_million(cheap.input_per_m, cheap.output_per_m,
                                           exec_in, exec_out)
        exec_cost_revisions = cost_per_million(cheap.input_per_m, cheap.output_per_m,
                                                int(exec_in * 0.1), int(exec_out * 0.1)) * revisions
        total_cost += (exec_cost_base + exec_cost_revisions) * t.share
        total_tokens += (exec_in + exec_out + (exec_in + exec_out) * 0.1 * revisions) * t.share

        # Verifier (mid)
        verifier_in = int(exec_out * 0.5)
        verifier_out = 200
        total_cost += cost_per_million(mid.input_per_m, mid.output_per_m,
                                        verifier_in, verifier_out) * t.share
        total_tokens += (verifier_in + verifier_out) * t.share

    return {
        "strategy": "p5_plan_then_execute",
        "cost_per_task": total_cost,
        "cost_per_1k": total_cost * 1000,
        "avg_tokens_per_task": total_tokens,
        "quality_vs_frontier": 0.98,  # spec frozen → near-frontier quality
        "assumptions": f"Cache hit rate={cfg.cache_hit_rate}; 2 revisions/task; spec freezable"
    }


def compute_p6_cross_cli_relay(cfg: Config) -> Dict[str, Any]:
    """Strategy: P6 Cross-CLI Relay — frontier plans/briefs, a separate coding-agent
    CLI executes, orchestrator reviews the diff and lands the commit.

    The worker prices at the target CLI's model. Config keys:
      - "p6_worker_tier": key into model_prices for the target CLI's model tier
        (defaults to "mid"). A local/self-hosted endpoint can be modeled by adding
        a price row with near-zero rates.
      - "p6_local_endpoint": if true, worker price is treated as ~0 (self-hosted).
    """
    frontier = cfg.model_prices["frontier"]
    mid = cfg.model_prices["mid"]

    worker_tier_key = getattr(cfg, "p6_worker_tier", None) or "mid"
    if worker_tier_key not in cfg.model_prices:
        worker_tier_key = "mid"
    worker = cfg.model_prices[worker_tier_key]
    local = bool(getattr(cfg, "p6_local_endpoint", False))

    total_cost = 0.0
    total_tokens = 0

    for t in cfg.task_distribution:
        base_in = t.avg_input_tokens
        base_out = t.avg_output_tokens

        # Planner (frontier): writes the self-contained brief (~15% of tokens)
        brief_in = int(base_in * 0.5)
        brief_out = int(base_out * 0.15)
        total_cost += cost_per_million(frontier.input_per_m, frontier.output_per_m,
                                        brief_in, brief_out) * t.share
        total_tokens += (brief_in + brief_out) * t.share

        # Worker (target CLI): executes the brief; full context re-read per dispatch
        # (separate process — no cache sharing with orchestrator)
        worker_in = base_in
        worker_out = base_out
        if not t.requires_frontier or True:  # target CLI executes all dispatchable work
            w = worker if not local else ModelPrice(worker.name, worker.tier, 0.0, 0.0)
            total_cost += cost_per_million(w.input_per_m, w.output_per_m,
                                            worker_in, worker_out) * t.share
        total_tokens += (worker_in + worker_out) * t.share

        # Orchestrator review of the diff (frontier, small context — diff only)
        review_in = int(base_out * 0.4)
        review_out = 150
        total_cost += cost_per_million(frontier.input_per_m, frontier.output_per_m,
                                        review_in, review_out) * t.share
        total_tokens += (review_in + review_out) * t.share

        # Gates re-run by orchestrator are deterministic (tests/lint) — cost 0 tokens

    return {
        "strategy": "p6_cross_cli_relay",
        "cost_per_task": total_cost,
        "cost_per_1k": total_cost * 1000,
        "avg_tokens_per_task": total_tokens,
        "quality_vs_frontier": 0.95,  # diff reviewed before landing; target CLI quality applies
        "assumptions": (f"Worker tier={worker_tier_key}"
                        + (" (local endpoint, ~0 marginal)" if local else "")
                        + "; fresh process per dispatch; no cross-process cache; review is diff-scoped")
    }


def main(args: argparse.Namespace) -> dict[str, Any]:
    cfg = load_config(args.config)

    results = {
        "always_frontier": compute_always_frontier(cfg),
        "p1_router": compute_p1_router(cfg),
        "p2_cascade": compute_p2_cascade(cfg),
        "p3_orchestrator_worker": compute_p3_orchestrator_worker(cfg),
        "p5_plan_then_execute": compute_p5_plan_then_execute(cfg),
        "p6_cross_cli_relay": compute_p6_cross_cli_relay(cfg),
    }

    # Find cheapest viable strategy (quality >= floor)
    viable = {k: v for k, v in results.items() if v.get("quality_vs_frontier", 1) >= cfg.quality_floor}
    if viable:
        cheapest = min(viable.items(), key=lambda x: x[1]["cost_per_task"])
        results["recommendation"] = {
            "strategy": cheapest[0],
            "reason": f"Lowest cost (${cheapest[1]['cost_per_1k']:.2f}/1k) while meeting quality floor ({cfg.quality_floor})"
        }

    # Warnings
    warnings = []
    if cfg.escalation_rate > results["p2_cascade"]["break_even_escalation_rate"]:
        warnings.append(
            f"P2 cascade escalation rate ({cfg.escalation_rate:.0%}) exceeds break-even "
            f"({results['p2_cascade']['break_even_escalation_rate']:.0%}) — "
            "cascade costs MORE than always-frontier"
        )
    if cfg.fan_out > 10:
        warnings.append(f"P3 fan-out ({cfg.fan_out}) > 10 — orchestrator context overflow risk (L3)")
    cheap_share = sum(t.share for t in cfg.task_distribution if not t.requires_frontier)
    if cheap_share > 0.85:
        warnings.append(
            f"Cheap-model share ({cheap_share:.0%}) > 85% — silent regression risk; "
            "ensure eval gate covers edge cases (P5)"
        )

    output = {
        "config": asdict(cfg),
        "strategies": results,
        "warnings": warnings,
        "notes": [
            "Token multipliers from Anthropic A2 (4× agent, 15× multi-agent) — treat as anchors, not predictions",
            "RouteLLM 85% savings on MT Bench at 95% quality (R1) — benchmark-specific",
            "Run your own eval with 50-500 cases before committing (A4, P5)"
        ]
    }

    if args.output:
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        json.dump(output, sys.stdout, indent=2)

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delegation cost calculator across P1-P6 patterns")
    parser.add_argument("config", help="Path to JSON config file")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    try:
        main(args)
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)