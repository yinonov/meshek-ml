# Phase 1: Approach & Colab Bootstrap - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure/documentation phase)

<domain>
## Phase Boundary

Document which ML methods were chosen and why (citing 8 academic papers), and set up a fresh Colab environment with dependencies and Drive access.

This phase produces two deliverables:
1. An APPROACH.md in the academic/ directory that maps each of the 8 collected papers to method decisions (LightGBM for forecasting, PPO for optimization, newsvendor as baseline, two-stage architecture, and explicitly deferred items).
2. A working Colab notebook bootstrap that installs dependencies and mounts Google Drive from a fresh runtime.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — infrastructure/documentation phase. The 7 ML approach decisions are already captured in PROJECT.md Key Decisions table and the approved plan. APPROACH.md should formalize these with full paper citations.

Key constraints:
- APPROACH.md must cite all 8 papers in academic/ by title and authors
- Each method choice must have a "why this and not alternatives" section
- Deferred items (pricing, E2E, federated) must have explicit rationale
- Colab bootstrap must work from a fresh runtime without manual repo surgery
- Dependencies should install from the package's pyproject.toml extras

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pyproject.toml` declares modular optional dependency groups (simulation, forecasting, optimization, federated, tracking, demo, dev)
- `notebooks/colab_quickstart.ipynb` already has a working notebook structure with simulation → PPO → newsvendor flow
- `academic/compass_artifact_wf-*.md` is the original research brief with detailed method comparisons

### Established Patterns
- Project uses Hydra for configuration, Pydantic for schemas
- Hebrew locale (Faker "he_IL") for merchant names
- Trackio for experiment tracking

### Integration Points
- APPROACH.md is a new file in academic/
- Colab notebook bootstrap cells go at the top of the existing notebook

</code_context>

<specifics>
## Specific Ideas

- The 8 papers are: original research brief, 6 arXiv papers (TCN-Attention, ARIMA+NLP, Dual-Agent DRL, DQN comparison, E2E with human knowledge, LSTM-Attention+PSO), and 2 journal papers (MARIOD/Sensors, ARIMA pricing/Sustainability)
- The professor specifically asked for scholarly evidence supporting the ML approach
- Decision rationale should be accessible to both the professor and team members

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
