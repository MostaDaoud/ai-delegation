# Model Tier Assignment Matrix

Default role→tier assignments. User overrides via `--tiers` or a local `model-tiers.json`. All tier names are **logical**, not model names — this file does not rot when models change.

---

## Tier Definitions

| Tier | Logical Meaning | Typical Price Band (per 1M tokens, mid-2026) | Capabilities |
|------|-----------------|---------------------------------------------|--------------|
| **frontier** | Strongest available reasoning, long context, tool use | $15–75 / $75–300 | Complex reasoning, ambiguity resolution, architectural judgment, multi-step planning, synthesis |
| **mid** | Strong execution, reliable code, good tool use | $3–15 / $15–60 | Code generation, structured extraction, drafting, translation (technical), mid-complexity reasoning |
| **cheap** | Fast, low-cost, narrow capabilities | $0.10–3 / $0.30–15 | Classification, short summarization, extraction, common-language translation, formatting |

> **Note:** Price bands are reference only. The `cost` sub-skill uses your actual price table.

---

## Default Role → Tier Mapping

| Role | Default Tier | Rationale | Can Downgrade If |
|------|-------------|-----------|------------------|
| **Decomposition / Planning** | frontier | This is what you pay frontier for — judgment, ambiguity resolution, architectural decisions | Never — this role owns the quality ceiling |
| **Ambiguity Resolution** | frontier | Upstream decisions that can't be written down must stay here (L1) | Never |
| **Final Synthesis** | frontier | Synthesizing worker outputs requires full reasoning + conflict resolution | Never |
| **Execution (frozen spec)** | cheap | Volume lives here; cheapest tier that clears the verifier | If verifier fails at cheap → mid |
| **Code Generation** | mid | Smallest models degrade fastest on code; mid is the floor for reliable output | If verifier passes at cheap → cheap (rare) |
| **Verification / Review** | mid | Independence beats capability; clean context matters more than model strength (C1) | Never below mid |
| **Classification / Extraction / Short Summary** | cheap | No measurable loss at cheap tier for bounded tasks | Never above cheap |
| **Translation (common languages)** | cheap | Well-supported languages work at cheap; rare languages need frontier | Rare languages → mid/frontier |
| **Translation (rare/technical)** | mid | Technical terminology needs stronger models | |
| **Long-Context Processing** | frontier/mid | Context window is a model property, not a tier property | |

---

## Capability → Tier Matrix

| Capability Required | Minimum Tier | Notes |
|---------------------|--------------|-------|
| Multi-step reasoning (5+ steps) | frontier | |
| Ambiguity resolution | frontier | |
| Architectural decisions | frontier | |
| Code generation (complex) | mid | |
| Code generation (boilerplate) | cheap | If verifier passes |
| Structured extraction (JSON schema) | cheap | |
| Short summarization (<2k tokens) | cheap | |
| Long summarization (>2k tokens) | mid | Context window |
| Common-language translation | cheap | EN↔ES, EN↔FR, EN↔DE, etc. |
| Rare-language translation | mid | |
| Technical translation | mid | |
| Classification (binary / few-class) | cheap | |
| Classification (many-class / nuanced) | mid | |
| Vision / image understanding | frontier | Only frontier models have vision (mid-2026) |
| Tool use (complex / multi-step) | frontier | |
| Tool use (simple / single-call) | mid | |
| Synthesis (conflicting worker outputs) | frontier | |

---

## How to Use This Matrix

1. The `decide` sub-skill outputs a `model_tiers` object mapping each role to a tier.
2. The `wire` sub-skill translates tiers to actual model names per harness using `platform-map.md`.
3. The `cost` sub-skill uses this matrix + your price table to compute costs.
4. **Override rule:** If your verifier fails at a tier, bump that role up one tier. Never bump planning/synthesis down.

---

## Tier-to-Model Mapping (Reference Only — Do Not Hardcode)

| Tier | Anthropic | OpenAI | Google | xAI | Local / Open-Weight |
|------|-----------|--------|--------|-----|---------------------|
| frontier | Opus / Fable | GPT-5 / o1-pro | Gemini 2.5 Pro / Ultra | Grok 4 / 5 | Llama 3.1 405B, Nemotron 3 Ultra |
| mid | Sonnet | GPT-4o / o1-mini | Gemini 2.5 Flash | Grok 3 | Llama 3.1 70B, Qwen 2.5 72B |
| cheap | Haiku | GPT-4o-mini / GPT-4.1-nano | Gemini 2.5 Flash-Lite | — | Llama 3.1 8B, Phi-4, Qwen 2.5 7B, Gemma 2 9B |

> **The skill never hardcodes these.** The `wire` sub-skill reads your harness config or a local `model-tiers.json` mapping tiers → model IDs.