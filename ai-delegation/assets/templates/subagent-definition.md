# Subagent Definition Template

Fill in all fields. A worker with missing fields fails the audit (AP1).

---

## Worker: {{WORKER_ID}}

**Role:** {{ROLE}} (e.g., researcher, code-writer, reviewer, extractor)

### Context Contract

**Objective:**
{{OBJECTIVE}}
> One sentence. What this worker must accomplish.

**Output Format:**
{{OUTPUT_FORMAT}}
> Exact format: "JSON with fields X, Y, Z" / "Markdown with sections A, B" / "Single file at path P"

**Tool Guidance:**
{{TOOL_GUIDANCE}}
> Which tools to use, which to avoid, search strategy (e.g., "search broad first, then narrow"; "prefer specialized tools over generic web search")

**Task Boundaries:**
{{TASK_BOUNDARIES}}
> What is OUT of scope. Prevents scope creep and duplicate work.

**Fan-Out Cap:** {{FAN_OUT_CAP}} (default: 5)

**Artifact Directory:** `.{{HARNESS}}/artifacts/{{WORKER_ID}}/`

**Verification Gate:**
{{VERIFICATION_GATE}}
> Type: clean_context_reviewer | deterministic_check | confidence_threshold
> Acceptance criteria: {{ACCEPTANCE_CRITERIA}}

**Escalation Trigger:**
{{ESCALATION_TRIGGER}}
> Explicit condition for moving up a tier. Never let the worker decide.

**Timeout:** {{TIMEOUT_SECONDS}}s (default: 300)

**Fallback on Failure:**
{{FALLBACK}}
> retry_with_better_brief | escalate_tier | handle_inline

---

## Example (Filled)

**Worker:** code-writer
**Role:** Implementation against frozen spec

**Objective:** Implement the feature described in the frozen spec at `.opencode/artifacts/spec/feature.md`, writing only the files listed in the spec's `files` section.

**Output Format:** JSON: `{"files_changed": ["path1", "path2"], "summary": "Implemented X and Y per spec", "confidence": 0.9}`

**Tool Guidance:** Use Read/Write/Edit on files in the spec. Do NOT search the web. Do NOT modify files outside the spec's `files` list. Run tests after each file if `test_command` provided in spec.

**Task Boundaries:** Do not make architectural decisions. Do not resolve ambiguities in the spec — escalate instead. Do not write tests unless explicitly listed.

**Fan-Out Cap:** 1 (this worker does not spawn children)

**Artifact Directory:** `.opencode/artifacts/code-writer/`

**Verification Gate:** Type: clean_context_reviewer. Acceptance: reviewer finds 0 severe bugs; all spec requirements implemented; tests pass.

**Escalation Trigger:** Spec ambiguity detected (missing field, conflicting requirements) → return `{escalate: true, reason: "..."}` to orchestrator.

**Timeout:** 600s

**Fallback on Failure:** retry_with_better_brief (max 2 retries), then escalate_tier.