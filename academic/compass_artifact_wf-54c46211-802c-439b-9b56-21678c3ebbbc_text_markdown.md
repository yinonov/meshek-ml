# Federated inventory optimization for perishable goods: a complete research brief

**Small boutique greengrocers can dramatically reduce spoilage and stockouts by combining demand forecasting, inventory optimization, and federated learning — all validated first on synthetic data.** This brief covers the four pillars of this ML project end-to-end: forecasting models, optimization methods, federated architecture, and simulation design. The recommended technical stack centers on LightGBM or XGBoost for forecasting (proven M5 competition winners), PPO-based reinforcement learning for ordering decisions, Flower for federated aggregation, and custom numpy/pandas simulation for synthetic data generation. Each component is designed to be beginner-accessible while remaining academically rigorous.

---

## 1. Demand forecasting: why LightGBM dominates perishable retail

### What makes perishable forecasting uniquely challenging

Forecasting demand for fruits and vegetables differs from standard retail in three critical ways. First, **shelf lives of 2–7 days** mean forecasting errors translate directly into waste (overstock) or lost sales (understock) — there's no "hold it until next month" option. Second, perishable demand is highly sensitive to external factors: warm weekends spike berry and salad demand by **30–50%**, while holidays can double baseline volumes. Third, asymmetric error costs are severe — predicting 110 kg of tomatoes when only 80 sell means 30 kg of pure waste at full purchase cost, whereas predicting 80 when you could have sold 110 loses only the margin on 30 units.

Forecast horizons for perishables must be **daily at the SKU-store level**. Weekly or monthly granularity is insufficient for items that spoil within days. Procurement decisions typically need 1–2 day lead times, so the practical requirement is a 1–3 day-ahead daily forecast per product per merchant.

### Model comparison for a beginner project

The table below summarizes the five main model families, ranked by their practical suitability:

| Model | Accuracy | Beginner-friendliness | Data needs | Best role |
|-------|----------|----------------------|------------|-----------|
| **LightGBM / XGBoost** | **Very high** | Moderate | Medium | **Primary production model** |
| Prophet | Moderate | Very easy | Low | Quick baseline, seasonal decomposition |
| ARIMA / SARIMA | Moderate | Moderate | Low (1+ year) | Statistical baseline |
| LSTM / GRU | High | Difficult | Very high | Only with large datasets |
| Temporal Fusion Transformer | Very high | Difficult | High | State-of-the-art stretch goal |

**LightGBM is the strongest practical choice.** In the M5 Forecasting Competition (42,840 Walmart time series, 5,558 teams), every top-5 winning solution used LightGBM as its core model, outperforming the best statistical methods by over **20%**. Tree-based models handle non-linear relationships, missing values, and mixed feature types naturally, and they integrate weather, holidays, promotions, and price effortlessly as input features. A 2023 MDPI study on perishable retail data confirmed that tree-based regressors outperformed LSTM on MAE, RMSE, MAPE, and R² specifically for perishable categories including meat and fruit.

**Prophet is the ideal starting point for a beginner.** Meta's additive decomposition model automatically handles seasonality, holidays, and trend changepoints with minimal configuration. It produces interpretable component plots (trend + weekly + yearly seasonality) that build intuition before moving to more complex models.

For a stretch goal, the **Temporal Fusion Transformer** (Lim et al., 2021) provides state-of-the-art multi-horizon forecasting with built-in interpretability (variable importance rankings, attention weights). It's available in the Darts and PyTorch Forecasting libraries. Foundation models like Google's TimesFM 2.0 and Amazon's Chronos show promise for zero-shot forecasting but haven't yet conclusively beaten well-tuned LightGBM on retail data.

### Essential features to engineer

The key features that drive perishable demand forecasting fall into five categories. **Seasonality** captures annual cycles (strawberries peak in summer, root vegetables in winter) and is best encoded via Fourier terms or sine/cosine transformations for neural models, or month/week indicators for tree-based models. **Day-of-week effects** are critical — Saturday demand at a greengrocer can be **30–40% above** weekday baseline, and Sunday often drops sharply. **Weather** (temperature, precipitation, sunshine hours) significantly impacts fresh produce; warm weather boosts demand for salads, fruits, and BBQ items. **Holidays** create demand spikes of 1.3–2.0× baseline and should be encoded as binary flags with days-until-holiday countdowns. **Price and promotions** drive demand elasticity that's especially pronounced for perishables.

For tree-based models, also engineer lag features (demand at t-1, t-7, t-14), rolling statistics (7-day mean, 14-day standard deviation), and interaction features (warm weekend = temperature × is_weekend).

### Where spoilage belongs in the pipeline

A key architectural insight: **forecast demand cleanly as unconstrained demand** (what would sell if the product were perfectly fresh), then handle spoilage and shelf life in the inventory optimization layer. The demand model predicts what customers want; the ordering algorithm decides how much to order given shelf-life constraints, safety stock needs, and expected waste. This separation simplifies both components. Christensen et al. (2021) demonstrated that incorporating shelf-life awareness into accuracy metrics — penalizing over-forecasting more heavily for shorter-lived products — improved freshness outcomes at Denmark's largest grocery wholesaler.

### Evaluation metrics: go asymmetric

Standard metrics each have a role: **MAE** communicates errors in units ("off by 5 kg on average"), **RMSE** penalizes large errors more heavily (important because large perishable errors create disproportionate waste), and **MAPE** enables cross-product comparison. **WMAPE** (weighted MAPE) is the industry standard used in the M5 competition.

For perishables, however, symmetric metrics miss the point. Over-forecasting is typically costlier than under-forecasting because unsold produce is pure waste at full purchase cost, whereas under-forecasting only loses the margin. Use **pinball loss (quantile loss)** with the quantile set by the newsvendor critical ratio: τ = C_underage / (C_underage + C_overage). This directly connects forecast evaluation to business cost optimization.

### Recommended library: Darts

The **Darts** library (by Unit8) provides a unified scikit-learn-style `fit()`/`predict()` interface across ARIMA, Prophet, XGBoost, LightGBM, LSTM, N-BEATS, TFT, and 20+ other models. It includes built-in backtesting, hyperparameter tuning, probabilistic forecasting, and covariate support. For a beginner project, Darts eliminates the need to learn separate APIs for each model family. Install with `pip install u8darts[all]`. The Nixtla ecosystem (StatsForecast, MLForecast, NeuralForecast) is a strong alternative with PyTorch Lightning integration.

### Key datasets

- **Corporación Favorita** (Kaggle Store Sales): Ecuadorian grocery chain with daily sales across 54 stores and 4,000+ products, including a perishable flag, promotions, holidays, and oil prices — the most relevant public dataset for this project
- **M5 Competition** (Kaggle): 42,840 Walmart daily time series with calendar events, prices, and SNAP dates — the industry-standard benchmark
- **Store Item Demand Forecasting Challenge** (Kaggle): 10 stores, 50 items, 5 years of clean daily data — ideal for prototyping
- **Open-Meteo API**: Free historical and forecast weather data globally, no API key required — essential for weather features
- **USDA Fruit and Vegetable Prices**: Retail prices for 153 produce items, useful for price feature calibration

---

## 2. Inventory optimization: from newsvendor to reinforcement learning

### Classical methods and their perishable-goods fit

Three classical models form the foundation. The **newsvendor model** is the most directly relevant: it handles single-period ordering with uncertain demand where unsold items are wasted — exactly the greengrocer's daily decision. The critical fractile formula `Q* = F⁻¹(Cu / (Cu + Co))` determines the optimal order quantity where Cu is the cost of understocking (lost margin) and Co is the cost of overstocking (purchase price minus salvage). For tomatoes bought at €5/kg and sold at €7/kg with no salvage: the critical ratio is 2/7 ≈ 0.29, meaning optimal orders target the **29th percentile** of demand — stocking conservatively because waste cost dominates.

The **(s, S) policy** orders up to level S whenever inventory drops to s. It works well for continuous review but **doesn't natively handle expiration** — you must track inventory age, not just total quantity, which breaks standard Markov assumptions. The **EOQ model** assumes no spoilage and constant demand, making it fundamentally unsuitable for perishables without extension. Ghare & Schrader (1963) and Covert & Phillips (1973) extended EOQ with exponential and Weibull deterioration functions, respectively, but these remain simplistic for real produce management.

The key limitation of all classical methods is that they optimize single decisions in isolation. Real inventory management is sequential: today's order affects tomorrow's available stock, which affects tomorrow's waste and ordering decisions.

### ML-enhanced optimization bridges forecast and decision

Two paradigms exist for connecting ML forecasts to ordering decisions. **Predict-then-optimize (two-stage)** trains the forecast model to minimize MSE, then separately plugs the forecast into a newsvendor or (s,S) formula. The problem: an MSE-optimal forecast is not necessarily a cost-optimal decision. **End-to-end (joint) optimization** trains the neural network directly with the newsvendor cost function as its loss, learning to produce outputs that minimize inventory costs rather than forecast error. Bertsimas & Kallus (2020, *Management Science*) showed that ML algorithms — KNN, kernel methods, random forests — can directly optimize order quantities from features without ever estimating demand distributions, a "data-driven newsvendor" approach that avoids error propagation.

### Reinforcement learning formalizes the sequential problem

RL is ideal for perishable inventory because it naturally handles the **sequential decision-making** structure: today's order affects tomorrow's state (leftover inventory ages by one day), and the agent learns to balance immediate costs against future consequences.

The **state space** must capture inventory by age: a vector `[i₁, i₂, ..., iₘ]` where `iⱼ` represents the quantity with j days of remaining shelf life, plus outstanding orders in transit, recent demand history, and calendar features (day-of-week, upcoming holidays). The **action space** is the order quantity — discrete for DQN (order 0, 5, 10, 15... units) or continuous for PPO/SAC (real-valued, then rounded). The **reward function** is profit per period:

```
R = revenue(sales) − purchase_cost(order) − holding_cost(inventory) − waste_penalty(expired) − stockout_penalty(unmet_demand)
```

The waste penalty and stockout penalty weights encode **asymmetric costs** — the core business reality that a spoiled crate of strawberries costs differently than a disappointed customer. These weights are the most important hyperparameters to calibrate.

### PPO is the recommended RL algorithm for beginners

| Algorithm | Action space | Stability | Complexity | Inventory evidence |
|-----------|-------------|-----------|------------|-------------------|
| **PPO** | Discrete or continuous | **Very stable** | Low | Nomura et al. (2025): <10% optimality gap vs. exact DP |
| DQN | Discrete only | Good | Low | De Moor et al. (2022): effective with reward shaping |
| A2C/A3C | Both | Moderate | Medium | Gijsbrechts et al. (2022, MSOM): matches or beats heuristics |
| SAC | Continuous | Good | High | Yavuz & Kaya (2024): 4.6% better than DQL on perishables |

**PPO (Proximal Policy Optimization)** is the most commonly recommended starting algorithm due to its stability, support for both discrete and continuous actions, and ease of tuning. Implement it using **Stable-Baselines3** (`pip install stable-baselines3[extra]`), which provides a clean API: define a custom Gymnasium environment, then train with `PPO("MlpPolicy", env).learn(total_timesteps=100000)`. The essential roadmap paper is Boute et al. (2022), "Deep reinforcement learning for inventory control: A roadmap" (*European Journal of Operational Research*), which catalogs all key design decisions for RL-based inventory systems.

### Handling asymmetric costs with pinball loss

The newsvendor critical fractile and pinball loss are mathematically identical: **τ = Cu / (Cu + Co)**. If stockout costs 3× more than waste, set τ = 0.75 (order the 75th percentile of demand). If waste costs 2× more than stockout, set τ = 0.33 (order conservatively). Any ML model — XGBoost, neural network — can be trained with pinball loss at the chosen τ to directly output the cost-optimal order quantity, bypassing the need for a separate optimization step.

### Multi-SKU challenges

Managing dozens of produce items simultaneously introduces substitution effects (customers buy conventional apples if organic are out), shared constraints (total budget, shelf space, supplier minimums), and state space explosion (N products × M age categories). The pragmatic beginner approach: optimize each SKU independently first, then add budget constraints via constrained optimization. Brandimarte (2023) released an open-source framework (github.com/DanieleGioia/PerishableDCM) modeling substitution between perishable products using discrete choice models — directly relevant for greengrocers.

### Key tools and environments

- **Stable-Baselines3**: PPO, DQN, A2C, SAC implementations — the standard RL library
- **Gymnasium**: The successor to OpenAI Gym for defining custom environments
- **OR-Gym** (github.com/hubbs5/or-gym): Pre-built RL environments for inventory management (InvManagement-v0 through v6)
- **Google OR-Tools**: For constrained multi-SKU optimization (budget, shelf space, MOQs)
- **scipy.optimize**: For classical newsvendor and EOQ calculations

---

## 3. Federated learning enables collective intelligence without data sharing

### Why federated learning fits this problem perfectly

Federated learning lets multiple merchants collaboratively train a shared model while keeping raw sales data local. Each greengrocer trains a local copy of the model on their own data, sends only **model weight updates** (not raw data) to a central server, which aggregates updates and returns an improved global model. This cycle repeats until convergence.

The business case is compelling. A single boutique merchant may have only a few months of data for 50–200 products — insufficient to train robust models alone. FL lets **10–50 merchants pool their learning** to capture broader demand patterns (seasonality, weather effects, holiday impacts) that no individual merchant could learn from their limited data. Crucially, merchants never share actual sales figures, pricing strategies, or customer volumes — preserving competitive sensitivity and GDPR compliance. Wang et al. (2022) demonstrated "Fed-LSTM" for supply chain demand forecasting across retailers, and FedTWA (2024) showed time-weighted aggregation improved demand forecasts on the Walmart dataset.

### FedAvg to FedProx: the right progression

**FedAvg** (McMahan et al., AISTATS 2017) is the foundational algorithm. Each round: the server sends the global model to selected clients, clients train locally for E epochs, clients send updated weights back, and the server computes a weighted average: `w_global = Σ (n_k / n_total) × w_k`. Key hyperparameters are E (local epochs), B (batch size), and C (client fraction per round). FedAvg reduces communication by **10–100×** versus distributed SGD.

**FedProx** (Li et al., MLSys 2020) adds one term to the local loss: `L_local + (μ/2)||w_local − w_global||²`. This proximal regularization prevents local models from drifting too far from the global model — critical when merchants have very different data distributions. The μ parameter controls the tightness of this constraint. FedProx is the recommended upgrade from FedAvg for heterogeneous merchant settings.

For this project, **start with FedAvg** (simplest to implement), then upgrade to **FedProx** once the non-IID challenges become apparent. Both are built into Flower as pre-built strategies requiring minimal code.

### The non-IID data problem and how to solve it

Non-IID (non-identically distributed) data is the central technical challenge. An urban premium greengrocer selling avocados and exotic fruits generates fundamentally different data than a rural market stall focused on potatoes and root vegetables. This heterogeneity causes **client drift** — local model updates pull in different directions, and naively averaging them degrades accuracy by up to **29%** compared to IID settings.

Three solution strategies apply, in order of increasing sophistication:

- **Local fine-tuning** (simplest): After FL converges, each merchant fine-tunes the global model on local data for a few extra epochs. This is the most beginner-friendly personalization approach.
- **APFL mixing** (Deng et al., 2020): Each merchant maintains a mixture `model = α × local_model + (1−α) × global_model`, where α is learned per client. This adaptively balances global knowledge with local specialization.
- **FedPer split architecture** (Arivazhagan et al., 2019): The neural network is split into shared base layers (aggregated globally) and personalized head layers (kept local). Base layers learn universal features; heads specialize per merchant.
- **Clustered FL** groups similar merchants (by metadata or gradient similarity) and trains separate federated models per cluster. FlexCFL (Duan et al.) achieved **+10.6% accuracy** on FEMNIST over FedAvg using this approach.

### Merchant metadata drives personalization without privacy risk

Non-sensitive metadata — store size, location type (urban/suburban/rural), pricing tier, product range breadth, years of operation — can be shared centrally to guide FL. Use k-means clustering on metadata feature vectors to form **3–5 merchant groups**, then either train a separate federated model per cluster or weight aggregation by metadata similarity. When a new merchant joins, their metadata immediately assigns them to the right cluster — solving the **cold start problem** without waiting for sales data to accumulate. The global model provides a warm initialization, and research on clustered FL shows new clients converge to target accuracy in **5–20 communication rounds** versus hundreds when training from scratch.

### Flower is the clear framework choice

A systematic comparison of 15 FL frameworks in *International Journal of Machine Learning and Cybernetics* (Springer, 2024) ranked **Flower (flwr)** first with an **84.75% overall score**. It's framework-agnostic (PyTorch, TensorFlow, scikit-learn, XGBoost, JAX), includes pre-built FedAvg and FedProx strategies, has a dedicated Flower Datasets library for data partitioning, provides built-in federated XGBoost tutorials, and has the largest FL community. Getting started: `pip install flwr` → `flwr new` → follow quickstart tutorials.

| Framework | Best for | Beginner-friendliness | Notes |
|-----------|---------|----------------------|-------|
| **Flower (flwr)** | **This project** | **Excellent** | Framework-agnostic, ranked #1, Apache 2.0 |
| TensorFlow Federated | TF users, simulation | Moderate | TensorFlow-only, primarily simulation |
| PySyft | Strict privacy (MPC, HE) | Steep curve | More privacy-focused than FL-focused |
| FATE | Enterprise production | Heavy setup | Docker-based, overkill for student project |
| FedML | Research + production | Good | Good all-around alternative |

### Architecture: federated XGBoost or small LSTM

For tabular sales data with engineered features, **federated XGBoost** (using Flower's built-in bagging aggregation) is the simplest starting point — it naturally handles non-IID data, is interpretable, and works well with small per-client datasets. For time-series approaches, a small **federated LSTM** trained with FedAvg/FedProx is the standard architecture demonstrated in Wang et al. (2022). With ~10 merchants, use **all clients per round** (C=1.0), E=5–10 local epochs, and aggregate daily or weekly. Expect convergence in **50–100 communication rounds**.

---

## 4. Simulation design: build synthetic data before touching real data

### Why simulation-first development works

Starting with synthetic data lets you build, test, and debug the entire ML pipeline — data ingestion, feature engineering, model training, federated communication, evaluation — before needing real data. You control the ground truth (you know what patterns exist because you created them), can generate unlimited data, and can test edge cases like holiday spikes or supply disruptions. The simulation also serves as the RL training environment: the agent interacts with the simulated inventory system during training.

### Custom numpy/pandas beats SimPy for this project

The SimPy documentation itself states: "SimPy is overkill for simulations with a fixed step size where your processes don't interact with each other or with shared resources." A daily-step inventory simulation — receive deliveries, process demand, check spoilage, place orders — is exactly this fixed-step pattern. **Custom numpy/pandas simulation is the recommended approach**: maximum flexibility, no extra libraries, produces DataFrames directly usable for ML, and every line of code is transparent.

Reserve SimPy for future extensions requiring within-day dynamics (customer arrival timing, variable delivery schedules). Mesa (agent-based modeling) and AnyLogic are overkill for synthetic data generation.

### Demand: use Negative Binomial, not Poisson

The Poisson distribution is the textbook starting point for count data, but real retail demand is consistently **overdispersed** (variance > mean). Agrawal & Smith (1996, *Naval Research Logistics*) demonstrated across a major retail chain that the **Negative Binomial fits significantly better** than Poisson or Normal. Chuang & Oliva (2014) confirmed this across 580 SKU-store datasets. Use Poisson for initial prototyping, then switch to Negative Binomial for realism.

Realistic daily demand parameters for a small greengrocer:

| Product | Mean daily demand | Distribution | Shelf life (days) |
|---------|------------------|--------------|-------------------|
| Tomatoes | 20 kg | NegBin(μ=20, α=3) | 5–7 |
| Bananas | 15 bunches | NegBin(μ=15, α=2) | 3–7 |
| Strawberries (summer) | 12 punnets | Poisson(λ=12) | 2–3 |
| Strawberries (winter) | 3 punnets | Poisson(λ=3) | 2–3 |
| Lettuce | 15 heads | NegBin(μ=15, α=2.5) | 3–5 |
| Apples | 18 kg | NegBin(μ=18, α=2) | 14–60 |
| Potatoes | 22 kg | NegBin(μ=22, α=2) | 30–90 |
| Dragon fruit | 2 units | ZI-Poisson(p₀=0.4, λ=2) | 5–7 |

### Layering seasonality, weekly patterns, and holidays

Use **multiplicative factors** applied to base demand:

```python
adjusted_demand = base_mu * seasonal_factor * weekly_factor * holiday_factor
daily_demand = np.random.negative_binomial(n=dispersion, p=dispersion/(dispersion + adjusted_demand))
```

**Annual seasonality** uses Fourier terms: `seasonal = 1.0 + 0.3 * sin(2π * day_of_year / 365) + 0.1 * cos(2π * day_of_year / 365)`, with product-specific amplitudes (strawberries: ±0.6 amplitude; potatoes: ±0.15). **Weekly patterns** use day-of-week multipliers: Monday 0.85, Friday 1.15, Saturday 1.30, Sunday 0.70 (or closed). **Holidays** are modeled as multiplicative spikes: Christmas week 1.5–2.0×, Easter 1.3×, summer bank holidays 1.2×. Prophet's default Fourier order is 10 for yearly and 3 for weekly seasonality — good calibration targets.

### Spoilage: Weibull decay with FIFO tracking

Model product quality degradation using the **Weibull distribution**: `quality(t) = exp(−(t/η)^β)` where η is the scale (related to expected shelf life) and β is the shape (β > 1 means accelerating deterioration — most realistic for produce). Items are "spoiled" when quality drops below a threshold (e.g., 0.3). A 2021 paper in *Computers & Industrial Engineering* fit Weibull models to real melon spoilage data and demonstrated significant accuracy improvements over simpler exponential decay.

Track inventory using **FIFO batches**: maintain a list of (quantity, age_in_days) tuples. Each day: age all batches by 1, remove batches exceeding shelf life (recording waste), and fulfill demand oldest-first. Realistic waste rates: berries 15–25%, leafy greens 10–20%, root vegetables 3–8%.

### Simulating merchant heterogeneity for federated learning

Create **3–5 merchant archetypes** with distinct profiles:

| Archetype | Daily customers | SKU count | Pricing | Demand scale |
|-----------|----------------|-----------|---------|-------------|
| Small urban boutique | 50–100 | 30–50, premium | High margin | 0.7× base |
| Medium suburban | 100–200 | 60–100, broad | Mid-range | 1.5× base |
| Market stall | 30–80 | 15–30, seasonal | Low margin | 0.5× base |
| Corner shop | 40–90 | 20–40, basics | Mid-high | 0.8× base |

The critical design principle for federated learning: **merchants share common patterns but differ in specifics.** All merchants exhibit strawberry summer peaks (shared seasonality), weekend demand lifts (shared weekly pattern), and holiday effects (shared). But they differ in demand scale, product mix (urban stocks more avocados; suburban more potatoes), price sensitivity, and local weather effects. Implement as: `merchant_demand = global_seasonality × merchant_scale × merchant_weekly × merchant_noise`, with per-merchant parameters drawn from archetype-specific distributions.

Use **Faker** to generate realistic merchant metadata (names, addresses, coordinates) and add structured attributes (size category, location type, pricing tier, years operating). This metadata drives federated clustering without exposing sales data.

### Existing tools worth adapting

Two open-source repositories are directly relevant. **RetailSynth** (github.com/RetailMarketingAI/retailsynth) is a multi-stage simulation calibrated on real grocery data (Dunnhumby Complete Journey), modeling customer shopping behavior across categories with Markov pricing models. **PerishableDCM** (github.com/DanieleGioia/PerishableDCM) specifically models perishable inventory with FIFO/LIFO tracking, weekly seasonality, consumer heterogeneity, and substitution between quality-differentiated products. Both provide reusable code and architectural patterns even if not used directly.

### Recommended simulation stack

```
numpy          → Demand generation (Poisson, NegBin, Weibull)
pandas         → DataFrames, date handling, output
scipy.stats    → Advanced distributions, KS tests for validation
Faker          → Merchant profile metadata
matplotlib     → Visualization and validation plots
```

For validation, compare synthetic data summary statistics against published benchmarks, check autocorrelation functions and seasonal decomposition, and use Kolmogorov-Smirnov tests to verify distributional assumptions.

---

## 5. Putting it all together: the project roadmap

### Incremental build order

The recommended implementation sequence builds complexity gradually, with each stage producing a testable, demonstrable result:

1. **Minimal simulation** (Week 1): 1 merchant, 5 products, Poisson demand, fixed shelf life, FIFO spoilage, numpy/pandas
2. **Enhanced simulation** (Week 2): Negative Binomial demand, multiplicative seasonality (weekly + annual), holiday effects, Weibull spoilage, 10 merchants with archetype profiles
3. **Demand forecasting** (Week 3): Prophet baseline → LightGBM with engineered features, evaluated on MAE/RMSE/WMAPE, using Darts library
4. **Inventory optimization** (Week 4): Newsvendor baseline → PPO agent in custom Gymnasium environment with Stable-Baselines3, asymmetric reward function
5. **Federated learning** (Week 5): Flower framework, FedAvg → FedProx, partition simulated data by merchant, compare federated vs. local-only vs. centralized performance
6. **Integration and evaluation** (Week 6): Full pipeline, cold-start experiments, personalization via local fine-tuning or APFL, final benchmarking

### Essential reading list

Five papers form the minimum theoretical foundation. **McMahan et al. (2017)**, "Communication-Efficient Learning of Deep Networks from Decentralized Data" — the original FedAvg paper. **Boute et al. (2022)**, "Deep reinforcement learning for inventory control: A roadmap" (*European Journal of Operational Research*) — the essential guide to RL for inventory. **Makridakis et al. (2022)**, "M5 accuracy competition: Results, findings, and conclusions" (*International Journal of Forecasting*) — proof that LightGBM dominates retail forecasting. **Fildes et al. (2022)**, "Retail forecasting: Research and practice" (*International Journal of Forecasting*) — the seminal survey. **De Moor et al. (2022)**, "Reward shaping to improve DRL in perishable inventory management" (*EJOR*) — directly addresses the perishable RL setup.

---

## Conclusion

This project sits at the intersection of four mature but independently studied fields — demand forecasting, inventory optimization, federated learning, and simulation — and the research reveals a clear technical path that's achievable for a beginner. The single most important insight is that **model choice matters less than pipeline architecture**: LightGBM with good features will outperform a poorly configured Transformer, and a well-shaped reward function matters more than the RL algorithm choice. The federated component adds genuine novelty to the project — FL for perishable inventory across heterogeneous small merchants is an underexplored area with only a handful of directly relevant papers, making this a legitimate research contribution rather than just an implementation exercise. Starting with simulation ensures every component can be validated against known ground truth before real-world complexity enters the picture.