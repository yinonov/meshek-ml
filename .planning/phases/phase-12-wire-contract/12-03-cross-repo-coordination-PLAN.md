---
phase: 12-wire-contract
plan: 03
type: execute
wave: 3
depends_on: ["12-01", "12-02"]
files_modified:
  - .planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md
autonomous: false
requirements: [WIRE-07]
tags: [cross-repo, typescript, handoff, manual-gate]

must_haves:
  truths:
    - "A cross-repo handoff document exists in this phase directory enumerating the exact meshek-side files, before/after diffs, and merge sequence."
    - "The handoff document references the merge order from CONTEXT.md: meshek PR (draft) → both reviewed → meshek merges first → meshek-ml merges after."
    - "The handoff document contains verbatim TypeScript before/after blocks for packages/types/src/recommendation.ts and the guard logic changes for packages/ml-client/src/guards.ts."
    - "The user has reviewed the handoff and confirmed the meshek-side PR is opened (or is ready to be opened) before the meshek-ml PR is approved for merge."
  artifacts:
    - path: ".planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md"
      provides: "Cross-repo coordination instructions, TypeScript diffs, merge sequence, PR URL placeholders"
      contains: "packages/types/src/recommendation.ts"
  key_links:
    - from: "12-03-CROSS-REPO-HANDOFF.md"
      to: "meshek repo packages/types/src/recommendation.ts and packages/ml-client/src/guards.ts"
      via: "before/after TypeScript blocks copied verbatim from 12-RESEARCH.md"
      pattern: "predicted_demand: number"
    - from: "12-03-CROSS-REPO-HANDOFF.md"
      to: "Phase summary (final)"
      via: "PR URL placeholders documented and filled by user"
      pattern: "(meshek PR|meshek-ml PR):"
---

<objective>
Produce the cross-repo handoff artifact for WIRE-07 — a single markdown document in the phase directory that enumerates exactly which meshek-side files need to change, the verbatim before/after diffs (copied from 12-RESEARCH.md), the locked merge sequence (meshek PR first, then meshek-ml), and PR-URL placeholders the user fills as both PRs go live. Then halt for the user to coordinate the cross-repo PR pair.

Purpose: This phase's CONTEXT.md and the v0.8 handoff brief both lock that the cross-repo PR pair is **coordinated by the user** — Claude must NOT attempt to push, open, or merge anything in the meshek repo. The deliverable here is a single high-fidelity handoff doc plus a manual gate that pauses execution until the user confirms the cross-repo state.

Output: `12-03-CROSS-REPO-HANDOFF.md` in the phase directory, plus a checkpoint that pauses for user confirmation before the phase summary is finalized.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/phase-12-wire-contract/12-CONTEXT.md
@.planning/phases/phase-12-wire-contract/12-RESEARCH.md
@.planning/phases/phase-12-wire-contract/12-VALIDATION.md
@.planning/phases/phase-12-wire-contract/12-01-SUMMARY.md
@.planning/phases/phase-12-wire-contract/12-02-SUMMARY.md
@docs/v0.8-meshek-ml-handoff.md

<interfaces>
<!-- The cross-repo files (in the meshek repo, NOT this repo) that the handoff doc must describe. -->
<!-- Do NOT edit these files from the meshek-ml session. The handoff doc enumerates what the user (or a separate session in the meshek repo) will edit. -->

meshek repo (companion to meshek-ml):
- packages/types/src/recommendation.ts — TypeScript interfaces for Signal, RecommendationLine, RecommendationResponse
- packages/ml-client/src/guards.ts — runtime shape guard (assertRecommendationResponse)
- packages/ml-client/src/guards.test.ts — fixtures + missing-field tests for the guard

The exact before/after TypeScript blocks are spelled out verbatim in 12-RESEARCH.md § "Cross-Repo Coordination — TypeScript Files Requiring Update" (lines 268-335). Copy them into the handoff doc unchanged.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write 12-03-CROSS-REPO-HANDOFF.md with verbatim TypeScript diffs, merge sequence, and PR URL placeholders</name>

  <files>.planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md</files>

  <read_first>
    - .planning/phases/phase-12-wire-contract/12-CONTEXT.md (Cross-Repo Coordination & Test Surface section)
    - .planning/phases/phase-12-wire-contract/12-RESEARCH.md (lines 266-336 — full "Cross-Repo Coordination" section with all TypeScript diffs)
    - docs/v0.8-meshek-ml-handoff.md (lines 134-138 — Cross-repo synchronization note)
    - .planning/phases/phase-12-wire-contract/12-01-SUMMARY.md (confirms Python wire contract landed)
    - .planning/phases/phase-12-wire-contract/12-02-SUMMARY.md (confirms full suite green)
  </read_first>

  <action>
    Per WIRE-07 and CONTEXT.md "Cross-Repo Coordination & Test Surface" — create the file `.planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md` with the following exact section structure:

    ```markdown
    # Phase 12 — Cross-Repo Coordination Handoff

    **Generated by:** plan 12-03
    **Status:** awaiting cross-repo PR pair
    **Locked merge sequence:** meshek PR (draft → review → merge) → then meshek-ml PR (review → merge)

    ## What Plan 12-03 Does NOT Do

    This plan does **not** edit, push, or merge anything in the meshek repo. The cross-repo PR is opened and merged by the user (or a separate Claude session running in the meshek repo with that repo's tooling). This document is the high-fidelity instruction set for that work.

    ## Files Requiring Changes in the meshek Repo

    Three files. All paths are relative to the meshek repo root.

    ### 1. `packages/types/src/recommendation.ts`

    **Before** (current shape — copy verbatim from this block when reviewing the PR diff):
    ```typescript
    export interface RecommendationLine {
      product_id: string;
      quantity: number;
      unit: string;
    }

    export interface RecommendationResponse {
      merchant_id: string;
      recommendations: RecommendationLine[];
      reasoning_tier: ReasoningTier;
      confidence_score: number;
      generated_at: string;
    }
    ```

    **After** (target shape):
    ```typescript
    export interface Signal {
      name: string;          // open string in v1.2; tightened to union in v1.3
      contribution: number;  // signed, in demand units (kg)
      copy_key: string;      // format: "signal.<snake_case_name>"
    }

    export interface RecommendationLine {
      product_id: string;
      unit: string;
      predicted_demand: number;
      demand_lower: number;
      demand_upper: number;
      reasoning_tier: ReasoningTier;
      confidence_score: number;
      signals: Signal[];
    }

    export interface RecommendationResponse {
      merchant_id: string;
      recommendations: RecommendationLine[];
      generated_at: string;
      // NOTE: reasoning_tier and confidence_score removed from response level
    }
    ```

    ### 2. `packages/ml-client/src/guards.ts` — `assertRecommendationResponse`

    **Remove** these response-level checks:
    - `r.reasoning_tier` access at the response level — REMOVE
    - `r.confidence_score` access at the response level — REMOVE
    - `l.quantity` per-line check — REMOVE

    **Add** these per-line checks inside the recommendations loop:
    - `typeof l.predicted_demand !== "number"` → shape error
    - `typeof l.demand_lower !== "number"` → shape error
    - `typeof l.demand_upper !== "number"` → shape error
    - `typeof l.reasoning_tier !== "string" || !REASONING_TIERS.has(l.reasoning_tier)` → shape error
    - `typeof l.confidence_score !== "number" || l.confidence_score < 0 || l.confidence_score > 1` → shape error
    - `!Array.isArray(l.signals) || l.signals.length < 1` → shape error

    The exact error message format follows the existing convention in guards.ts (read the file in the meshek repo to match style).

    ### 3. `packages/ml-client/src/guards.test.ts`

    The current `valid` fixture in this test file uses the old shape (top-level `reasoning_tier` / `confidence_score` and per-line `quantity`). Update the fixture to use the new shape (per-line `predicted_demand`, `demand_lower`, `demand_upper`, `reasoning_tier`, `confidence_score`, and `signals: [...]`). Add missing-field and wrong-type tests for each new line-level field.

    ## Merge Sequence (LOCKED — do not deviate)

    Per CONTEXT.md "Cross-Repo Coordination & Test Surface" and the v0.8 handoff brief:

    1. **Open the meshek PR as a draft FIRST.** This signals to anyone on the meshek side that the wire change is coming and gives them a place to comment.
    2. Finish the meshek-ml PR (the changes shipped in plans 12-01 and 12-02).
    3. Get **both** PRs reviewed.
    4. **Merge the meshek PR FIRST**, then merge the meshek-ml PR.
    5. Document both PR URLs in the phase summary (next section).

    Rationale: meshek's `@meshek/ml-client` runtime guard would crash against the new wire shape if meshek-ml shipped first. Sequencing the meshek PR ahead means meshek's tests pass against both old and new shapes during the brief window where the deployed meshek-ml is still on v1.1.

    ## PR URLs (filled by user as PRs go live)

    - **meshek PR (TypeScript types + guard + guard test):** `<URL — fill in when opened>`
    - **meshek-ml PR (this phase):** `<URL — fill in when opened>`
    - **meshek PR merged at:** `<commit SHA or merge timestamp — fill in after merge>`
    - **meshek-ml PR merged at:** `<commit SHA or merge timestamp — fill in after merge>`

    ## Verification (manual, by user)

    Per 12-VALIDATION.md "Manual-Only Verifications" table:

    1. Open meshek PR (draft) updating the three files above.
    2. Get both PRs reviewed.
    3. Merge meshek PR first.
    4. Merge meshek-ml PR.
    5. Verify the meshek build pipeline (`pnpm build` or equivalent in meshek repo) passes against the new TypeScript types.
    6. Verify the meshek-side guard tests (`pnpm test packages/ml-client`) pass against the new guard logic.
    7. Document URLs above.
    ```

    Do NOT add anything beyond this template — no aspirational text, no "future work" notes, no v1.3 references. The handoff doc is a single-purpose instruction set.

    Do NOT attempt to access the meshek repo from this Claude session. Do not run `git clone`, `gh pr create`, or any cross-repo git operations.
  </action>

  <verify>
    <automated>test -f .planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md && grep -c 'predicted_demand: number' .planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md | awk '$1 >= 1 {exit 0} {exit 1}'</automated>
  </verify>

  <acceptance_criteria>
    - `test -f .planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md` (file exists)
    - `grep -c 'packages/types/src/recommendation.ts' .planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md` returns at least 1
    - `grep -c 'packages/ml-client/src/guards.ts' .planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md` returns at least 1
    - `grep -c 'packages/ml-client/src/guards.test.ts' .planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md` returns at least 1
    - `grep -c 'predicted_demand: number' .planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md` returns at least 1
    - `grep -c 'demand_lower: number' .planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md` returns at least 1
    - `grep -c 'signals: Signal\[\]' .planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md` returns at least 1
    - `grep -c 'Merge the meshek PR FIRST' .planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md` returns at least 1
    - `grep -c '<URL — fill in when opened>' .planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md` returns at least 2 (one slot for each PR)
    - The file does NOT contain any text that suggests Claude opened, pushed, or merged a cross-repo PR — verify: `grep -iE 'gh pr create|git push|git clone' .planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md` returns 0 lines
  </acceptance_criteria>

  <done>
    Handoff doc exists with all three meshek-repo file references, verbatim TypeScript before/after blocks, the locked merge sequence, and PR URL placeholders. No cross-repo git operations were attempted from this session.
  </done>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 2: Pause for user to coordinate the cross-repo PR pair</name>

  <files>.planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md (read-only — user fills PR URL placeholders)</files>

  <what-built>
    - `.planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md` — full instruction set for the meshek-side PR
    - All Python-side wire contract changes (plans 12-01, 12-02) shipped and tested
  </what-built>

  <how-to-verify>
    1. Read `.planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md`.
    2. Open a PR in the meshek repo with the changes described in sections 1–3 of the handoff doc (or run a separate Claude Code session in the meshek repo to do it).
    3. Open this phase's meshek-ml PR (`gh pr create` from the current meshek-ml branch — but DO NOT merge yet).
    4. Once both PRs are reviewed: merge the meshek PR FIRST, then merge the meshek-ml PR.
    5. Fill in the four PR URL / merge SHA placeholders in `12-03-CROSS-REPO-HANDOFF.md`.
    6. Confirm here when both PRs are merged (or when the meshek PR is merged and the meshek-ml PR is queued).
  </how-to-verify>

  <resume-signal>Type "merged" (both PRs merged) or "ready" (handoff complete, meshek PR landed, meshek-ml PR queued) or describe blockers.</resume-signal>

  <action>
    Halt execution and wait for the user to coordinate the cross-repo PR pair per the handoff doc and the steps in `<how-to-verify>` above. This is a `checkpoint:human-action` task — Claude takes no automated action here. Do NOT attempt `gh pr create` against the meshek repo, do NOT merge the meshek-ml PR until the user confirms the meshek PR is merged first, and do NOT auto-fill the PR URL placeholders in the handoff doc.
  </action>

  <verify>
    <automated>grep -c 'merged at' .planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md</automated>
  </verify>

  <acceptance_criteria>
    - User has typed "merged" or "ready" or described blockers (resume signal received)
    - The four PR URL / merge SHA placeholders in `12-03-CROSS-REPO-HANDOFF.md` are filled in by the user (verify with `grep -c '<URL — fill in when opened>' .planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md` returns 0 if "merged"; ≥1 acceptable if "ready" or "blocked")
  </acceptance_criteria>

  <done>
    User has confirmed the cross-repo PR pair status. The phase summary can now be finalized with the actual PR URLs documented in the handoff file.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| meshek-ml repo ↔ meshek repo | Cross-repo trust; coordinated by the user, not by Claude |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-12-06 | Tampering | Cross-repo merge order | mitigate | Handoff doc explicitly locks "merge meshek PR first" with rationale; checkpoint task forces user acknowledgment before phase summary is finalized |
| T-12-07 | Repudiation | PR URL traceability | mitigate | Handoff doc reserves four PR URL / SHA slots so the merge pair is permanently documented in the planning artifact |
</threat_model>

<verification>
- `12-03-CROSS-REPO-HANDOFF.md` exists in `.planning/phases/phase-12-wire-contract/`
- File contains all required sections (file refs, before/after diffs, merge sequence, URL placeholders)
- No cross-repo git operations were attempted from this session
- User has acknowledged the cross-repo PR pair status via the checkpoint
</verification>

<success_criteria>
- WIRE-07 has a concrete, executable hand-off artifact instead of a vague "open a PR" instruction
- The locked merge sequence is recorded in a phase artifact (not just CONTEXT.md, which can be revised)
- The user's manual coordination is gated by a checkpoint, so the phase summary cannot be finalized until both PRs are merged or the user explicitly defers
</success_criteria>

<output>
After the user resumes from the checkpoint, create `.planning/phases/phase-12-wire-contract/12-03-SUMMARY.md` documenting:
- The two PR URLs (filled in by user in the handoff doc)
- The merge order actually executed (should match the locked sequence)
- Any deviations from the locked sequence and why
- Confirmation that this phase's PR is merged (or the explicit deferral state if not yet)
</output>
