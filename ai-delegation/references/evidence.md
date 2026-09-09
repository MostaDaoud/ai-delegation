# Evidence Base — AI Delegation

All claims in this skill trace to these sources. Each claim carries **confidence** and a `refresh_due` date. When in doubt, run the `audit` sub-skill with `--refresh` to re-verify.

---

## First-Party (vendor engineering blogs)

| ID | Claim | Source | Confidence | refresh_due |
|----|-------|--------|------------|-------------|
| A1 | Orchestrator-worker (Opus lead + Sonnet subagents) beat single-agent Opus by **90.2%** on Anthropic internal research eval | [Anthropic, "How we built our multi-agent research system", 2025-06-13](https://www.anthropic.com/engineering/multi-agent-research-system) | High — self-reported, no independent replication | 2026-12-13 |
| A2 | Agents ≈ **4×** chat tokens; multi-agent ≈ **15×** chat tokens | same | High | 2026-12-13 |
| A3 | **Token usage alone explains 80%** of BrowseComp variance; 95% with tool calls + model choice | same | High | 2026-12-13 |
| A4 | Effort-scaling: simple fact-find = 1 agent / 3–10 calls; direct compare = 2–4 subagents / 10–15 calls each; complex = >10 subagents | same | High | 2026-12-13 |
| A5 | 3–5 subagents in parallel + 3+ parallel tool calls per subagent cut research time up to **90%** | same | High | 2026-12-13 |
| A6 | Vague briefs caused duplicate work (e.g., 1 subagent on 2021 chip crisis, 2 duplicating 2025 supply chains) | same | High | 2026-12-13 |
| A7 | Subagent output to filesystem + lightweight references avoids "game of telephone" | same (Appendix) | High | 2026-12-13 |
| C1 | Clean-context reviewer catches avg **2 bugs/PR**, **~58% severe**, on agent-written PRs | [Cognition, "Multi-Agents: What's Actually Working", 2026-04-22](https://cognition.com/blog/multi-agents-working) | High | 2026-10-22 |
| C2 | Multi-agent works when **writes stay single-threaded**; extra agents contribute intelligence, not actions | same | High | 2026-10-22 |
| C3 | "Smart friend" (advisor) fails with asymmetrically weaker primary — "how does a dumber model know it's at its limits?" is an open training problem | same | High | 2026-10-22 |
| C4 | Cross-frontier advisor routing **works**; delegation logic becomes a **capability router, not a difficulty escalator** | same | High | 2026-10-22 |
| C5 | Managers default to **over-prescription** when lacking codebase context; agents assume shared state with children; child→sibling comms don't happen by default | same | High | 2026-10-22 |
| C6 | Practical shape is **map-reduce-and-manage**; unstructured swarms "mostly a distraction" | same | High | 2026-10-22 |
| C7 | Principle 1: share context, and share **full agent traces, not just messages**. Principle 2: **actions carry implicit decisions**, conflicting decisions = bad results | [Cognition, "Don't Build Multi-Agents", 2025-06-12](https://cognition.com/blog/dont-build-multi-agents) | High | 2026-12-12 |

---

## Peer-Reviewed / Benchmark

| ID | Claim | Source | Confidence | refresh_due |
|----|-------|--------|------------|-------------|
| R1 | RouteLLM: **85% cost saving** on MT Bench at **95% GPT-4 quality**; strong model needed on **14%** of queries | [RouteLLM, ICLR 2025](https://arxiv.org/abs/2406.18665) | High — benchmark-specific (MT Bench, GPT-4-Turbo vs Mixtral 8x7B) | 2026-12-31 |
| R2 | BERT-classifier router: **45%** cost saving on MMLU at comparable quality | same | Medium-High | 2026-12-31 |
| R3 | FrugalGPT: cascade cheap→strong with learned verifier | [arXiv 2305.05176](https://arxiv.org/abs/2305.05176) | High | 2026-12-31 |
| R4 | LLMRouterBench: 33 models, 21 datasets, 10 routing algorithms, 400K instances, ~1.8B tokens | [arXiv 2601.07206](https://arxiv.org/abs/2601.07206), Findings@ACL 2026 | High | 2027-01-31 |
| R5 | DELEGATE-52: LLMs **corrupt documents in long delegated editing workflows** across 52 professional domains | [Microsoft Research, Apr 2026](https://www.microsoft.com/en-us/research/publication/llms-corrupt-your-documents-when-you-delegate) | High — strongest counter-evidence | 2026-10-31 |

---

## Reported / Practitioner (label as reported, not law)

| ID | Claim | Source | Confidence | refresh_due |
|----|-------|--------|------------|-------------|
| P1 | Router overhead: rules **<1 ms**, embeddings **~5 ms**, ML classifiers **50–100 ms** vs 500–2000 ms LLM | [digitalapplied, 2026-06-14](https://www.digitalapplied.com/blog/llm-model-routing-2026-cost-quality-optimization-engineering-guide) | Medium | 2026-12-14 |
| P2 | Orchestrator-worker **raises quality ceiling, does not cut cost**; model routing cuts spend **1.4–3.7×** | [Duet, 2026-07-18](https://duet.so/blog/frontier-model-orchestrator) | Medium — directionally confirmed by A2 | 2026-12-18 |
| P3 | Production split: 60–70% cheap / 30–40% frontier ≈ **37–46%** cost reduction; 80/20 ≈ **72%** | digitalapplied | Low-Medium — model-derived | 2026-12-14 |
| P4 | Persistent "sidekick" worker: cached tokens ≈ **10%** of fresh input; **delegate down, don't escalate up** (advisor re-reads full transcript as fresh tokens) | [aibuilderclub, 2026-07-22](https://www.aibuilderclub.com/blog/orchestrator-worker-sidekick-paradigm) | Medium — token accounting is sound | 2026-12-22 |
| P5 | Silent quality regression is the hidden tax; mitigate with 50–500 case pre-merge eval gate | digitalapplied | Medium — consistent with A4 | 2026-12-14 |

---

## YouTube Practitioner (mined for failure modes + phrasing; NOT used as factual sources)

| Video | Channel | Views | Why it matters |
|-------|---------|-------|----------------|
| [Hermes Agent Masterclass: 8. Subagents & Delegation](https://www.youtube.com/watch?v=_6DtQkDpcEs) | Tonbi's AI Garage | 9.1K | Best articulation of "cheap children, strong parent" + "subagents know nothing" rule; live cost comparison |
| [How to Build Claude Subagents Better Than 99% of People](https://www.youtube.com/watch?v=e18sdZLwP7o) | Nate Herk | 78K | Subagent scoping practice |
| [How to Build Claude Agent Teams Better Than 99% of People](https://www.youtube.com/watch?v=vDVSGVpB2vc) | Nate Herk | 314K | Persistent/resumable workers — sidekick pattern |
| [My Multi-Agent Team with OpenClaw](https://www.youtube.com/watch?v=bzWI3Dil9Ig) | Brian Casel | 766K | Highest-reach real multi-agent build log |
| [What Are Orchestrator Agents?](https://www.youtube.com/watch?v=X3XJeTApVMM) | IBM Technology | 88K | Canonical neutral explanation |
| [What is an LLM Router?](https://www.youtube.com/watch?v=V_K6PCmdtRg) | Sam Witteveen | 35K | Routing layer fundamentals |
| [RouteLLM: 85% Lower Cost](https://www.youtube.com/watch?v=dmMzMtqM_P0) | Mervin Praison | 3.8K | Router implementation walkthrough |
| [Orchestrating Subagents: Sidekick Paradigm](https://youtu.be/wCSPgHpcxdc) | aibuilderclub | — | Companion to sidekick article; cross-harness demos |
| [Orchestrator–Worker Pattern Explained](https://www.youtube.com/watch?v=rpHmyg8zPNQ) | — | — | Pattern basics |
| [LLM Router Explained in 10 Minutes](https://www.youtube.com/watch?v=SRSzcukpZlA) | Amine DALY | 571 | Recent, concise |
| [Your LLM Cost Dashboard Is Lying](https://www.youtube.com/watch?v=CinFq9I81m4) | tokensandtraces | 50 | Counter-evidence: cheaper routing can raise total cost |

---

## P6 Cross-CLI Relay Source (delegate-skills)

| ID | Claim | Source | Confidence | refresh_due |
|----|-------|--------|------------|-------------|
| DS1 | Review-first loop: brief → dispatch → poll → review diff → **orchestrator lands the commit**; "the relay never commits" is a stated invariant of every dispatch | [amElnagdy/delegate-skills](https://github.com/amElnagdy/delegate-skills), README "How delegation works" | High — stated invariant, contract-tested per CLI | 2026-12-08 |
| DS2 | Enforcement limits are measured and documented: aider commits by default (must force-disable `--auto-commits`/`--dirty-commits`); grok cannot be prevented from writing headlessly; `touchedFiles` is post-run `git status` and cannot show ignored/reverted/out-of-repo writes; Command Code `--yolo` is full-trust with no path restriction; some CLIs discard queued stdout on exit (thin report = missing info, not failed run) | same, README "Verification status" + footnotes | Medium-High — per-CLI live/contract runs documented, OS coverage partial (several CLIs unverified on native Windows) | 2026-12-08 |
| DS3 | Fleet lanes: work-type → implementer binding with dials; explicit flags override lane dials; wrong implementer for a lane fails loud; project lane config is **content-bound to explicit setup approval** and cloned/edited configs **fail closed** until re-approved (`delegate-fleet.v1` schema) | same, README "Create a fleet" + delegate-setup references/schema.md | Medium-High — contract-tested in their smoke suite | 2026-12-08 |
| DS4 | Result contract `delegate-relay.result.v1`: status, exitCode, signal (with host-killed hint), implementer's final report, `touchedFiles`, sessionId where exposed | same, README "How delegation works" | High — stated contract, shape verified | 2026-12-08 |

---

## Gate-Depth Source (plan-gate)

| ID | Claim | Source | Confidence | refresh_due |
|----|-------|--------|------------|-------------|
| PG1 | The read-only gate holds (byte-for-byte untouched files in a session mode where permission settings are ignored) — BUT on a well-specified task it bought nothing: ungated agent 76k tokens / 14 tools / 162s, correct and clean; gated plan-only 26k / 8 / 119s, wrote nothing. **Honest default: do not gate** — use the one-line implicit-decision report most days; full-gate only when the work is genuinely uncertain | [AgriciDaniel/plan-gate](https://github.com/AgriciDaniel/plan-gate), README "What testing showed" + evidence/ | Medium — controlled A/B but **single run per arm** (their own stated limit) | 2026-12-08 |
| PG2 | Codex cannot pause, gain write permission, and resume in the same session — the read-only pass and the write pass must be **two fresh runs**, with the approved plan carrying the context; confirmed by live run and openai/codex#33974. Also: an empty plan can exit 0 and read like a valid empty plan (sandbox no-op) — preflight and treat empty as failure | same, README "What testing showed" + "Known limits" | High — live run + upstream issue | 2026-12-08 |
| PG3 | "Restrict the capability, do not ask the model nicely. A prompt telling a model not to write is not a gate, in any runtime." Gate-depth levels: none / one-line ("Report anything you decided that the task did not specify.") / full; gate when >3 files, root-causing (not localizing), fuzzy requirements, or two agents on the same files | same, README "Use it" | High — stated method, enforcement tested (Lane A tool allowlist, Lane B OS sandbox) | 2026-12-08 |

---

## How to Use This Table

- The skill's `decide` sub-skill loads this file and presents the **confidence** for any claim it cites.
- The `audit` sub-skill can re-verify claims and update `refresh_due`.
- Never present reported numbers (P1–P5) as expectations — always qualify: "Anthropic reported X on their internal eval; your mileage depends on your task mix and eval gate."