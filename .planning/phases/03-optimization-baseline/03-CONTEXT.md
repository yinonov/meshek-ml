# Phase 3: Optimization Baseline - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Wire the already-functional PPO agent and newsvendor baseline into the Colab notebook with side-by-side benchmarking metrics.

The notebook already has PPO training and newsvendor comparison sections (Sections 7-9). This phase ensures they use the parameter cell values (SEED) and that a clear comparison table with fill_rate, waste_rate, stockout_frequency is displayed.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user setting. The existing notebook sections 7-9 already contain working PPO training, newsvendor comparison, and episode visualization. The main work is:
1. Ensure the PPO/newsvendor sections use SEED from the parameter cell
2. Ensure the comparison table clearly shows fill_rate, waste_rate, stockout_frequency
3. Optionally implement scripts/run_optimization.py (currently a stub)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (ALL FUNCTIONAL)
- `src/meshek_ml/optimization/env.py` — PerishableInventoryEnv (Gymnasium)
- `src/meshek_ml/optimization/ppo_agent.py` — train_ppo() via Stable-Baselines3
- `src/meshek_ml/optimization/newsvendor.py` — optimal_order_negbin()
- `src/meshek_ml/optimization/rewards.py` — CostParams, compute_reward()
- `src/meshek_ml/optimization/evaluation.py` — compute_inventory_metrics()

### Current Notebook State
- Section 7: PPO training (already works)
- Section 8: PPO vs Newsvendor evaluation (already works, shows comparison table)
- Section 9: Episode visualization (already works)
- The existing code uses hardcoded seed values — needs to use SEED parameter

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
