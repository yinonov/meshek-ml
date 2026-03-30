# ML Approach: Academic Evidence and Method Decisions

This document maps every method choice in the meshek-ml project to the academic papers that support it. The project builds a demand forecasting and inventory optimization pipeline for small Israeli greengrocers selling perishable produce, where daily ordering errors translate directly into spoiled goods (overstock) or lost sales (understock). The stakes are asymmetric: a crate of unsold strawberries is a total loss, while a missed sale loses only the margin.

The architecture follows a two-stage design: first forecast demand, then optimize the ordering decision. This separation keeps each component independently testable and debuggable, which matters for a research codebase that must be presentable to both the course professor and the development team. The alternative --- end-to-end optimization that trains the forecaster directly on inventory cost --- is academically superior (Paper 5 demonstrates this) but is explicitly deferred to v2 after the two-stage baseline is stable.

Every method decision below is grounded in the eight academic papers collected in this directory. Where a paper argues against our chosen approach, we cite the contrary evidence and explain why we defer the alternative rather than ignoring it. The goal is scholarly honesty: a reader should be able to trace each choice to its supporting literature, understand what was considered and rejected, and know exactly what is left for future work.

## Paper Reference Table

| ID | Title | Authors | Year | File |
|----|-------|---------|------|------|
| P1 | Optimization decision model of vegetable stock and pricing based on TCN-Attention and genetic algorithm | Xia, Zhang, Wen | 2024 | 2403.01367v1.pdf |
| P2 | Automated vegetable pricing and restocking based on data analysis and nonlinear programming | Ma Mingpu | 2024 | 2409.09065v1.pdf |
| P3 | Dual-Agent Deep Reinforcement Learning for Dynamic Pricing and Replenishment | Zheng, Li, Jiang, Peng | 2024 | 2410.21109v1.pdf |
| P4 | A Study of Data-driven Methods for Inventory Optimization | Lee, Wong, Tan | 2025 | 2505.08673v1.pdf |
| P5 | Deep Learning for Perishable Inventory Systems with Human Knowledge | Liao, Peng, Rong | 2026 | 2601.15589v1.pdf |
| P6 | Integrating Attention-Enhanced LSTM and Particle Swarm Optimization for Dynamic Pricing and Replenishment Strategies in Fresh Food Supermarkets | Liu, Zhang, Zhang, Hou, Guo, Tian, Liu | 2025 | 2509.12339v1.pdf |
| P7 | Multi-Agent Deep Reinforcement Learning for Integrated Demand Forecasting and Inventory Optimization in Sensor-Enabled Retail Supply Chains (MARIOD) | Yang, Wang, Wang, Li, Zhou | 2025 | sensors-25-02428-v2.pdf |
| P8 | ARIMA-Driven Vegetable Pricing and Restocking Strategy for Dual Optimization of Freshness and Profitability in Supermarket Perishables | Li, Liu, Qiu, Zhou, Zhang, Wang, Guo | 2024 | sustainability-16-04071.pdf |

## Method Decisions

### 1. Demand Forecasting: LightGBM

**Why this method.** LightGBM is the proven workhorse for tabular retail forecasting. In the M5 Forecasting Competition (42,840 Walmart time series, 5,558 teams), every top-5 winning solution used LightGBM as its core model. Tree-based models handle mixed feature types (numerical weather data alongside categorical day-of-week indicators), missing values, and non-linear relationships naturally. They integrate calendar features, weather, holidays, and price as input features without the extensive preprocessing that neural architectures require. For a research codebase running on Google Colab, LightGBM offers the best accuracy-to-complexity ratio.

**Supporting evidence.** P4 (Lee, Wong, Tan) directly compares tree-based models against LSTM and traditional time series methods on perishable product categories, confirming that tree models outperform deep learning on MAE, RMSE, MAPE, and R-squared. P7 (MARIOD, Yang et al.) uses a Temporal Fusion Transformer for forecasting but requires 8x A100 GPUs for training --- entirely infeasible for a Colab environment. The original research brief (Compass artifact) documents the M5 competition results and the MDPI 2023 study confirming tree-based regressors outperform LSTM specifically for perishable categories including meat and fruit.

**Why not alternatives.**
- **ARIMA / SARIMA**: P2 (Ma Mingpu) and P8 (Li et al.) both use ARIMA-based approaches, but ARIMA is limited to linear relationships and requires separate models per product-merchant combination. It cannot incorporate exogenous features (weather, holidays) as naturally as LightGBM.
- **LSTM / Attention-LSTM**: P6 (Liu et al.) uses attention-enhanced LSTM with particle swarm optimization, achieving good results but requiring substantially larger datasets and longer training times. The attention mechanism adds interpretability but at the cost of complexity that is unjustified given our data volume.
- **TCN-Attention**: P1 (Xia et al.) combines temporal convolutional networks with attention, but this deep learning architecture requires more data and compute than our Colab constraint allows.
- **Temporal Fusion Transformer**: P7 (MARIOD) uses TFT for state-of-the-art multi-horizon forecasting, but its hardware requirements (8x A100 GPUs) make it impractical for our execution environment.

### 2. Inventory Optimization: PPO

**Why this method.** Proximal Policy Optimization (PPO) handles the sequential decision-making structure of daily perishable ordering: today's order affects tomorrow's available stock, which affects tomorrow's waste and ordering decisions. PPO supports continuous action spaces (real-valued order quantities), trains stably without extensive hyperparameter tuning, and integrates cleanly with the Stable-Baselines3 ecosystem. The Gymnasium environment interface makes the inventory simulation directly usable as a training environment.

**Supporting evidence.** The foundational reference is Boute et al. (2022), "Deep reinforcement learning for inventory control: A roadmap" (European Journal of Operational Research), which catalogs all key design decisions for RL-based inventory systems and positions PPO as the recommended starting algorithm. P4 (Lee, Wong, Tan) compares deep reinforcement learning favorably against time series and random forest approaches for inventory optimization, demonstrating that RL agents learn policies that account for sequential dependencies that myopic methods miss. P3 (Zheng, Li, Jiang, Peng) validates DRL for replenishment decisions in a dual-agent architecture, confirming that policy gradient methods handle the ordering action space effectively. Nomura et al. (2025) report less than 10% optimality gap between PPO and exact dynamic programming solutions.

**Why not alternatives.**
- **DQN**: Discrete actions only, requiring coarse ordering granularity (order 0, 5, 10, 15... units). For perishable goods where the optimal order can vary by single units, this discretization loses precision without compensating benefits.
- **SAC (Soft Actor-Critic)**: Higher implementation complexity with marginal gains. P4 (Lee, Wong, Tan) finds SAC competitive but not decisively better than PPO for inventory problems, and SAC's maximum entropy framework adds conceptual overhead.
- **A2C/A3C**: Gijsbrechts et al. (2022, MSOM) show A2C matching or beating heuristics, but PPO's clipped objective provides more stable training without the need to tune the entropy coefficient carefully.

### 3. Analytical Baseline: Newsvendor

**Why this method.** The newsvendor model is the classical single-period ordering model for perishable goods under uncertain demand. Its critical fractile formula --- `Q* = F_inverse(C_underage / (C_underage + C_overage))` --- directly maps to the greengrocer's daily decision: how much to order given that unsold produce spoils and unmet demand means lost sales. The formula is closed-form, interpretable, and provides a natural bridge between forecast output (demand distribution) and ordering action. Any RL agent must demonstrably beat this baseline to justify its added complexity.

**Supporting evidence.** All eight papers in this collection reference or build upon the newsvendor framework. P5 (Liao, Peng, Rong) goes furthest by embedding the newsvendor structure as a prior inside their end-to-end neural architecture (E2E-PIL), demonstrating that the newsvendor solution provides useful inductive bias even for deep learning approaches. P8 (Li et al.) uses the newsvendor as the baseline for their ARIMA-driven restocking strategy, confirming its role as the standard benchmark in perishable inventory research. The critical fractile also connects directly to pinball loss for forecast evaluation --- the quantile at which we evaluate forecasts should match the newsvendor critical ratio.

**Why not alternatives.**
- **(s, S) policy**: Requires continuous inventory tracking with age awareness, breaking standard Markov assumptions for perishable goods. More complex to implement without proportional accuracy gains for our single-period daily ordering use case.
- **EOQ (Economic Order Quantity)**: Assumes no spoilage and constant demand, making it fundamentally unsuitable for perishable goods without substantial extensions.

### 4. Architecture: Two-Stage (Forecast then Optimize)

**Why this method.** The two-stage architecture separates demand forecasting from inventory optimization: first predict how much customers will want, then decide how much to order. This separation keeps each component independently testable, debuggable, and presentable. The forecaster can be evaluated on standard metrics (MAE, RMSE, WMAPE) independently of the optimizer, and the optimizer can be tested against analytical baselines (newsvendor) using known demand distributions. This modularity matches the existing codebase structure and makes the pipeline easier to explain to the course professor.

**Supporting evidence.** P4 (Lee, Wong, Tan) uses the two-stage approach successfully, training forecasting models separately from optimization policies. P5 (Liao, Peng, Rong) acknowledges two-stage as the standard approach and uses it as the baseline against which their end-to-end method (E2E-PIL) is compared.

**Why not alternatives.**
- **End-to-End (E2E-PIL)**: P5 (Liao, Peng, Rong) demonstrates that training the neural network directly with the newsvendor cost function as its loss (rather than MSE) produces better inventory outcomes. Their E2E-PIL approach outperforms the two-stage baseline. However, it requires a neural forecasting model (not compatible with LightGBM) and adds architectural complexity. This is the planned v2 upgrade path.
- **Data-driven newsvendor (Bertsimas & Kallus, 2020)**: Directly maps features to order quantities without explicit demand estimation. Elegant but removes the interpretability of having a separate forecast step, which is valuable for team understanding and academic presentation.

### 5. Simulation as Training Ground

**Why this method.** Real sales data from small Israeli greengrocers is scarce --- a single merchant may have only a few months of data for 50-200 products, insufficient for robust model training. Synthetic data generation provides controlled experiments where ground truth is known (because we defined the data-generating process), unlimited training volume, and the ability to test edge cases (holiday spikes, supply disruptions, new product introductions) that may not appear in limited real data. The simulation also doubles as the RL training environment: the PPO agent interacts with the simulated inventory system during training.

**Supporting evidence.** P5 (Liao, Peng, Rong) uses both synthetic and real-data experiments, validating their approach first on simulation before moving to actual retail data. P7 (MARIOD, Yang et al.) validates on simulated sensor data across their multi-agent architecture. The original research brief confirms the simulation-first approach, recommending custom numpy/pandas simulation over frameworks like SimPy because daily-step inventory simulation is a fixed-step pattern that does not need event-driven complexity.

**Why not alternatives.**
- **Real data only**: Insufficient volume for a small-merchant setting. Models trained on limited real data overfit to local patterns and cannot generalize to seasonal shifts not yet observed in the training window.
- **SimPy or Mesa**: Over-engineered for daily-step simulation. The SimPy documentation itself states it is overkill for fixed-step simulations where processes do not interact with shared resources.

## Explicitly Deferred

### Dynamic Pricing

**What it is.** Treating price as a decision variable alongside ordering quantity, optimizing both jointly to maximize profit.

**Why deferred.** P3 (Zheng, Li, Jiang, Peng) demonstrates that the joint profit function for pricing and replenishment is not jointly concave, requiring a specialized dual-agent architecture where one agent handles pricing and another handles ordering at different timescales. P1 (Xia, Zhang, Wen) and P6 (Liu et al.) both couple pricing with inventory optimization but add significant model complexity --- genetic algorithms in P1's case, particle swarm optimization in P6's. For a v1 pipeline that must run in Colab and be presentable as a course project, this complexity is unjustified.

**When.** Version 2, after the single-merchant forecast-optimize pipeline is stable. The price field is recorded in the data schema for forward compatibility, so enabling pricing requires no schema migration.

### End-to-End Forecast-Optimize

**What it is.** Training a neural network directly with the inventory cost function (newsvendor loss) as its objective, rather than the traditional MSE loss for forecast accuracy. This produces forecasts that are optimized for ordering decisions rather than point accuracy.

**Why deferred.** P5 (Liao, Peng, Rong) shows that their E2E-PIL approach (embedding the newsvendor structure as a differentiable layer inside the neural network) outperforms the two-stage baseline. The evidence is clear that end-to-end is better. However, the two-stage architecture is simpler to debug, matches the current codebase separation between `forecasting/` and `optimization/` modules, and provides interpretable intermediate outputs (the forecast itself) that are valuable for academic presentation and team understanding.

**When.** Version 2, building on the stable two-stage baseline. The transition path is well-defined: replace the LightGBM forecaster with a neural model, then replace the MSE training loss with P5's newsvendor-embedded cost function.

### Federated Learning

**What it is.** Using the Flower framework to train models across multiple heterogeneous merchants without sharing raw sales data. Each merchant trains locally and shares only model weight updates, enabling collective intelligence while preserving data privacy.

**Why deferred.** Federated learning for perishable inventory across heterogeneous small merchants is the novel research contribution of this project --- the aspect that moves it beyond a course exercise into genuine research. However, FL requires a stable single-merchant pipeline as its foundation. Training a federated model on a broken local pipeline would produce meaningless results. The federation milestone is a separate phase that depends on the forecasting and optimization components being individually validated.

**When.** After this milestone (single-merchant Colab pipeline) completes successfully. The simulation already generates multi-merchant heterogeneous data with archetype profiles, providing the data infrastructure that FL needs.

### Attention-Based Interpretability

**What it is.** Using attention mechanisms in neural forecasting models to identify which input features (weather, day-of-week, holidays) drive demand predictions, providing interpretable explanations alongside forecasts.

**Why deferred.** P1 (Xia, Zhang, Wen) uses TCN-Attention, P6 (Liu et al.) uses LSTM-Attention, and P7 (MARIOD, Yang et al.) uses Transformer attention. All three demonstrate that attention weights provide meaningful interpretability. However, attention requires a deep learning forecasting model. Our v1 uses LightGBM, which provides feature importance rankings as its native interpretability mechanism --- a simpler but adequate alternative for the current milestone.

**When.** If and when deep learning forecasting models (LSTM, TFT) are added to the pipeline, attention-based interpretability becomes a natural addition.

## Paper-to-Decision Mapping

| Decision | Supporting Papers | Contrary Evidence |
|----------|------------------|-------------------|
| LightGBM for forecasting | P4 (tree models outperform LSTM), P7 (as contrast --- TFT needs 8x A100s) | P6 (LSTM+Attention works well), P1 (TCN-Attention effective) |
| PPO for optimization | P3 (DRL for replenishment), P4 (DRL vs classical methods) | --- |
| Newsvendor baseline | P5 (embedded as structural prior), P8 (used as baseline), all 8 papers reference it | --- |
| Two-stage architecture | P4 (uses two-stage successfully), P5 (uses it as baseline) | P5 (E2E-PIL outperforms two-stage) |
| Simulation first | P5 (synthetic + real experiments), P7 (simulated sensor data) | --- |
| Defer dynamic pricing | P1, P3, P6 (all demonstrate the complexity of coupling pricing with inventory) | --- |
| Defer E2E optimization | P5 (demonstrates E2E-PIL is superior to two-stage) | --- |
| Defer federated learning | --- (novel contribution, no contrary evidence --- just sequencing) | --- |

## References

1. Xia, Zhang, Wen (2024). "Optimization decision model of vegetable stock and pricing based on TCN-Attention and genetic algorithm." arXiv:2403.01367v1.

2. Ma Mingpu (2024). "Automated vegetable pricing and restocking based on data analysis and nonlinear programming." arXiv:2409.09065v1. (Chinese)

3. Zheng, Li, Jiang, Peng (2024). "Dual-Agent Deep Reinforcement Learning for Dynamic Pricing and Replenishment." arXiv:2410.21109v1.

4. Lee, Wong, Tan (2025). "A Study of Data-driven Methods for Inventory Optimization." arXiv:2505.08673v1.

5. Liao, Peng, Rong (2026). "Deep Learning for Perishable Inventory Systems with Human Knowledge." arXiv:2601.15589v1.

6. Liu, Zhang, Zhang, Hou, Guo, Tian, Liu (2025). "Integrating Attention-Enhanced LSTM and Particle Swarm Optimization for Dynamic Pricing and Replenishment Strategies in Fresh Food Supermarkets." arXiv:2509.12339v1.

7. Yang, Wang, Wang, Li, Zhou (2025). "Multi-Agent Deep Reinforcement Learning for Integrated Demand Forecasting and Inventory Optimization in Sensor-Enabled Retail Supply Chains (MARIOD)." Sensors, 25, 2428.

8. Li, Liu, Qiu, Zhou, Zhang, Wang, Guo (2024). "ARIMA-Driven Vegetable Pricing and Restocking Strategy for Dual Optimization of Freshness and Profitability in Supermarket Perishables." Sustainability, 16, 4071.
