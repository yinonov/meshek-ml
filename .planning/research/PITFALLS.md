# Domain Pitfalls

**Domain:** Open-source ML inference service for perishable inventory — adding FastAPI to an existing ML research codebase, targeting small greengrocers
**Project:** meshek-ml v1.1 Merchant Order Advisor
**Researched:** 2026-04-10
**Confidence:** MEDIUM-HIGH

---

## Scope Note

This file supersedes the v1.0 pitfalls (Colab bootstrap, synthetic vs. real data, temporal leakage). Those pitfalls are validated and resolved. This document covers new pitfalls introduced by:

1. Adding a FastAPI inference API to the existing ML pipeline
2. Persisting per-merchant sales history
3. Building a cold-start-aware recommendation engine
4. Operating as an open-source project targeting a niche vertical

---

## Critical Pitfalls

### Pitfall 1: Blocking the FastAPI Event Loop with Synchronous ML Inference

**What goes wrong:**
LightGBM and the newsvendor calculation are synchronous and CPU-bound. If `model.predict()` is called directly inside an `async def` endpoint, it blocks the entire uvicorn event loop. While one merchant's recommendation is computing, all other requests queue. Under load, this manifests as timeout cascades rather than graceful slowdown.

**Why it happens:**
FastAPI's async model is well-suited for I/O-bound work (database calls, HTTP requests). ML inference is CPU-bound. Developers familiar with Flask bring synchronous patterns into FastAPI without accounting for the event loop.

**How to avoid:**
Use plain `def` (not `async def`) for the `/recommend` endpoint — FastAPI automatically runs synchronous endpoints in a thread pool. Only use `async def` for endpoints that genuinely await I/O. This is the correct pattern for CPU-bound ML inference without adding any async infrastructure.

```python
# Correct for CPU-bound ML inference
@app.post("/recommend")
def recommend(request: RecommendRequest) -> RecommendResponse:
    result = pipeline.run(request)
    return result

# Wrong — blocks the event loop
@app.post("/recommend")
async def recommend(request: RecommendRequest) -> RecommendResponse:
    result = pipeline.run(request)  # CPU work blocks the loop
    return result
```

**Warning signs:**
- p99 latency is 10x p50 latency under concurrent load.
- A single slow recommendation request freezes all other endpoints (including health checks).
- `uvicorn` logs show requests queuing rather than failing fast.

**Phase to address:** API foundation phase (Phase 1 of v1.1)

---

### Pitfall 2: Loading ML Models on Every Request

**What goes wrong:**
LightGBM model deserialization from disk takes 50-200ms per load. If model loading happens inside the request handler (or on each worker restart), the first request after any worker cycle pays this cost. In the worst case, models are reloaded on every call — making the service appear to work in testing but fail under any realistic throughput.

**Why it happens:**
Research notebooks load models at the top of a cell. Developers copy this pattern into FastAPI route handlers without considering request lifecycle.

**How to avoid:**
Load all models once at application startup using FastAPI's `lifespan` context manager (introduced in FastAPI 0.93, preferred over the deprecated `@app.on_event`). Store models in a module-level or app-state dictionary. For LightGBM, use the native `.txt` format (`model.booster_.save_model("model.txt")` / `Booster.load_model("model.txt")`) rather than Python-version-sensitive serialization formats.

```python
from contextlib import asynccontextmanager
from lightgbm import Booster

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.lgbm_model = Booster(model_file="models/lgbm.txt")
    app.state.newsvendor = NewsvendorConfig.load()
    yield

app = FastAPI(lifespan=lifespan)
```

**Warning signs:**
- First request after restart is 5-10x slower than subsequent requests.
- Memory usage grows steadily under load (multiple model copies loaded).
- High variance in response times that does not correlate with request complexity.

**Phase to address:** API foundation phase

---

### Pitfall 3: No Cold-Start Strategy Leads to Silent Nonsense Recommendations

**What goes wrong:**
When a new merchant is onboarded with zero sales history, the LightGBM pipeline either crashes (missing features), returns a prediction of zero, or extrapolates from whatever default state emerges from empty feature computation. Any of these is worse than an explicit fallback. Merchants receiving a "0 units" recommendation on day one lose trust permanently.

**Why it happens:**
ML pipelines are designed around sufficient data. Cold-start is an edge case in research contexts but the common case in production for a growing service. The distinction between "no data yet" and "error" is not enforced at the pipeline boundary.

**How to avoid:**
Define the recommendation tier explicitly in the API contract before writing any code:

1. **No history (< 7 days):** Return category-level defaults from a hardcoded table (e.g., "tomatoes: 5 kg"). Log the tier used.
2. **Sparse history (7-30 days):** Return newsvendor recommendation with wide confidence intervals.
3. **Sufficient history (> 30 days):** Return LightGBM forecast-backed recommendation.

The API response should include a `recommendation_basis` field (`"default" | "newsvendor" | "ml_forecast"`) so the meshek app can display appropriate context to the merchant. This also gives you observability into how many merchants are in each tier.

**Warning signs:**
- The `/recommend` endpoint returns `200 OK` with `quantity: 0` for new merchants.
- No logging distinguishes between "predicted 0" and "insufficient data, used default."
- Merchants report that the tool "doesn't work" in their first week.

**Phase to address:** Cold-start recommendation phase

---

### Pitfall 4: Conflating the API Schema with the Internal Pipeline Schema

**What goes wrong:**
The existing `src/meshek_ml/forecasting/schema.py` defines a strict internal schema (`date`, `merchant_id`, `product`, `quantity`). If FastAPI request/response models are built as thin wrappers around these internal Pydantic models, any future change to the internal schema breaks the public API contract — and vice versa. This coupling creates schema drift where pipeline changes silently invalidate the API.

**Why it happens:**
Reusing existing Pydantic models feels like DRY (Don't Repeat Yourself). It is actually premature coupling of two separate concerns: the API's public contract and the pipeline's internal data contract.

**How to avoid:**
Define separate Pydantic models for the API layer (`RecommendRequest`, `RecommendResponse`) and the pipeline layer (`ForecastInput`, `ForecastOutput`). Write explicit conversion functions between them. The API models should be stable and versioned; the pipeline models can evolve freely.

**Warning signs:**
- A change to `schema.py` breaks an API test.
- An API field name change requires editing a pipeline feature function.
- The `response_model` on a FastAPI endpoint references an internal domain object.

**Phase to address:** API foundation phase

---

### Pitfall 5: Per-Merchant Storage Without Isolation Causes Data Leakage

**What goes wrong:**
If per-merchant sales history is stored in a shared SQLite file with only a `merchant_id` column separating tenants, a missing `WHERE merchant_id = ?` clause in any query leaks one merchant's data to another. For a single-developer project this is unlikely but not impossible; once contributors join, it becomes a real risk. More concretely: model features computed from another merchant's data produce confidently wrong recommendations.

**Why it happens:**
Single-file SQLite feels simpler than per-merchant files. The isolation burden is shifted to application code, which is only as reliable as every SQL query written by every contributor.

**How to avoid:**
Use one SQLite file per merchant stored in a directory keyed by `merchant_id`. The filesystem provides isolation by default — no query-level bug can cross tenant boundaries. The tradeoff is managing many small files, but at meshek-ml's scale (dozens to low hundreds of merchants) this is negligible. If a shared DB is chosen for operational reasons, add a mandatory middleware layer that injects `merchant_id` into every query context and enforce it in code review.

**Warning signs:**
- A recommendation for merchant A contains product names that merchant A never sold.
- SQL queries in the codebase do not always filter by `merchant_id`.
- New contributors write queries without knowing the multi-tenancy requirement.

**Phase to address:** Sales history persistence phase

---

### Pitfall 6: Hebrew Text Parsing Fails Silently on Encoding or Normalization Differences

**What goes wrong:**
WhatsApp messages sent by Israeli greengrocers arrive in UTF-8 Hebrew but may include mixed-direction text (Hebrew + numbers + product names in both Hebrew and English), non-standard Unicode normalization, and marketplace slang. A dictionary-based parser that matches on normalized strings will silently fail to parse valid inputs, returning "unrecognized product" when the actual issue is a Unicode normalization mismatch or a character that looks identical visually but differs in codepoint.

**Why it happens:**
Dictionary lookups in Python work on exact string equality. Hebrew Unicode normalization (NFC vs. NFD) and final-letter forms (כ vs. ך) are common sources of invisible mismatches. Developers testing with ASCII or copied-and-pasted Hebrew from a text editor miss these.

**How to avoid:**
- Normalize all incoming strings to NFC before any dictionary lookup: `unicodedata.normalize('NFC', text)`.
- Build the product dictionary with both the canonical form and common variants (including English transliterations like "tamato" for עגבנייה).
- Log every parse attempt with its normalized form, matched result, and confidence. Never fail silently.
- Add test fixtures with actual WhatsApp-sourced Hebrew strings, not programmer-typed Hebrew.

**Warning signs:**
- Parse tests pass but real WhatsApp messages frequently return "unrecognized product."
- The same product name copied from WhatsApp vs. typed in a test produces different hashes.
- No logging of parse failures makes the failure rate invisible.

**Phase to address:** Hebrew input parsing phase

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Reuse internal Pydantic models as API response models | Saves 20 lines | Pipeline changes break API clients; schema coupling across layers | Never — always define separate API models |
| Single SQLite file for all merchants with `merchant_id` filter | Simpler setup | Any query bug leaks cross-merchant data; harder to delete one merchant's data | Only if strict code review enforces it and merchant count stays < 10 |
| Load ML models inside request handlers | Faster to write | 50-200ms overhead on every warm request; unpredictable latency | Never in production |
| No `recommendation_basis` field in response | One less field to define | Impossible to distinguish "predicted 0" from "no data"; poor observability | Never — the cost is one enum field |
| `async def` endpoint for CPU inference | Looks "correct" for FastAPI | Blocks event loop under any concurrency; hard to debug | Never — use plain `def` for CPU-bound work |
| Skip API versioning (`/v1/recommend`) until needed | Avoids over-engineering | Breaking changes require meshek app changes and coordinated deploys | Acceptable at v1.1 if documented as technical debt |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| meshek Fastify backend → meshek-ml FastAPI | Calling `/recommend` without a timeout, assuming LAN speed | Set explicit HTTP timeout (5-10s); handle 503 gracefully; the FastAPI service may be on a different host |
| LightGBM model persistence | Saving with Python-version-sensitive serialization formats | Use `model.booster_.save_model("model.txt")` (LightGBM native format) and `Booster.load_model()` |
| Per-merchant SQLite → FastAPI | Opening a new DB connection per request | Use a connection pool or a single module-level connection with `check_same_thread=False` |
| WhatsApp text → Hebrew parser | Receiving text with mixed RTL/LTR markers (`\u200f`, `\u200e`) | Strip Unicode direction markers before parsing |
| Cold-start defaults table → API | Hardcoding defaults in code | Store defaults in a config file (YAML or JSON) so they can be updated without a code deploy |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Feature engineering runs full history on every request | Response time grows linearly with merchant history length | Cache the latest feature vector; only recompute when new sales data arrives | After ~60 days of data per merchant |
| Full re-training LightGBM on every recommendation request | Endpoint takes 30+ seconds | Train once (batch job or on sales update); serve pre-trained model | Immediately — even 10 rows of data |
| No pagination on sales history reads | Memory grows unbounded as history grows | Read only the last N days needed for features (max lag window + buffer) | After ~1 year of daily data per merchant |
| Returning full raw feature vectors in API responses | Response payload grows with feature count | API response contains only business-level fields; features are internal | At feature count > 50 |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| No authentication on `/recommend` | Any caller can query any merchant's recommendation by guessing `merchant_id` | Add a shared secret header or API key; meshek app holds the key |
| `merchant_id` taken from request body without validation | Merchant A queries merchant B's history | Tie `merchant_id` to authentication context, not request payload |
| Storing raw WhatsApp message text in sales history | Privacy risk; WhatsApp messages may contain PII beyond product names | Parse and store only structured fields (`date`, `product`, `quantity`); discard raw text |
| Model files served as static assets | Proprietary training data or feature logic exposed | Never expose model artifacts via the HTTP server; keep them out of the public static directory |

---

## UX Pitfalls (Merchant-Facing)

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Recommendation with no context ("order 8 kg") | Merchant has no reason to trust a number from an unknown system | Include `recommendation_basis` in API response; meshek app displays "based on your last 14 days" |
| All-or-nothing: works perfectly or fails completely | Merchant abandons the tool after first failure | Implement the three-tier fallback (default → newsvendor → ML) so the tool always returns something reasonable |
| Forcing merchants to use structured input before seeing value | Zero adoption — merchants on WhatsApp will not learn a format | Accept free-text Hebrew first; parse imperfectly; show the result with a confirmation step |
| Silent model degradation over time | Recommendations quietly worsen as market conditions change | Log MAE against recent actual sales (if available); surface model health to the developer, not the merchant |

---

## Ecosystem Map: Existing Open-Source Projects

This section addresses whether meshek-ml is entering a crowded space or genuine whitespace.

### Direct Competitors (Perishable Inventory + ML)

| Project | Stars (approx.) | What it does | Gap vs. meshek-ml |
|---------|-------|-------------|-------------------|
| `fvizpal/inventory-optimisation-using-machine-learning` | < 50 | Jupyter notebooks for perishable goods ML | No API, no WhatsApp, no Hebrew, no deployment path |
| `ztjhz/food-stock-demand-forecast` | < 100 | Time series forecasting for food demand | Academic exercise; no production path |
| `Erdos1729/food-demand-forecasting` | < 50 | Food demand ML notebooks | Dataset-specific; no generalization |

### Adjacent Projects (Demand Forecasting / Supply Chain)

| Project | Stars (approx.) | What it does | Relevance |
|---------|-------|-------------|-----------|
| `ikatsov/tensor-house` | ~1,300 | Enterprise ML notebooks including supply chain RL | Educational reference; notebook-only; multi-echelon focus |
| `frePPLe/frepple` | ~1,500 | Full open-source ERP / supply chain planning | Enterprise-focused, complex setup; no ML inference API; MIT community edition |
| `oneapi-src/demand-forecasting` | < 200 | Intel-backed TensorFlow demand forecasting kit | Reference architecture; no deployment |
| `anshul-musing/multi-echelon-inventory-optimization` | < 100 | Multi-echelon RL with SimPy | Research-only |

### Food Waste Adjacent (Not ML Forecasting)

| Project | Stars (approx.) | What it does | Relevance |
|---------|-------|-------------|-----------|
| `openfoodfoundation/openfoodnetwork` | ~1,000+ | Food distribution marketplace | Operational platform; different problem |
| GitHub `food-waste` topic repos | Mixed (< 200 each) | Donation/redistribution apps | Consumer-facing; not inventory ML |

**Verdict (MEDIUM confidence):** There is genuine whitespace. No open-source project combines (a) perishable goods ML forecasting, (b) a deployable inference API, (c) a WhatsApp-first merchant interface, and (d) academic grounding. The closest is `tensor-house` but it is an educational notebook collection, not a service. meshek-ml has a plausible claim to being the first production-oriented open-source ML ordering tool for single-store greengrocers.

---

## Open-Core Licensing Recommendation

**Recommendation: MIT for meshek-ml (the ML service); proprietary for meshek (the WhatsApp + dashboard app).**

Rationale:

- **MIT for meshek-ml** is correct. The ML pipeline, FastAPI inference service, forecasting code, and academic grounding are the parts developers and researchers want to study, fork, and contribute to. MIT removes all friction. This is the "core" that builds community.
- **Proprietary for meshek** (the companion app) is the natural moat. WhatsApp Business API integration, merchant onboarding UX, and the dashboard are where the product value lives for end users. Keeping this proprietary enables a future SaaS business without license conflicts.
- **Avoid AGPL for meshek-ml.** AGPL is designed to prevent cloud providers from hosting without contributing back. At this stage it adds legal friction for potential enterprise adopters and contributors without meaningful protection.
- **Avoid dual licensing at this stage.** Dual licensing (permissive + commercial) is appropriate when you have enterprise customers needing license exceptions. That is a later-stage problem.

What to keep open (in meshek-ml):
- LightGBM forecasting pipeline
- Newsvendor + PPO optimization
- FastAPI inference server and schema definitions
- Synthetic data generator
- Academic approach documentation

What to keep proprietary (in meshek):
- WhatsApp webhook integration and message routing
- Merchant dashboard and onboarding flow
- LLM-based message interpretation (the `llm-engine`)
- Multi-merchant management and billing

**Confidence: MEDIUM.** This matches the standard open-core model used by Seldon, frePPLe, and comparable ML infrastructure projects. The specific split (ML pipeline open, app layer proprietary) aligns with the architecture split already in place between the two repos.

---

## Promotion Strategy

### Target Audiences

1. **ML/data science developers** who want a real-world RL + LightGBM production example (the academic angle is a hook).
2. **Food tech / agri-tech developers** building in emerging markets.
3. **Israeli tech community** — local angle, Hebrew language support is unique.
4. **Academic researchers** studying perishable goods, supply chain RL, or food waste reduction.

### Concrete Channels (Prioritized)

**High signal, low noise:**

1. **Hacker News "Show HN"** — The strongest single channel for developer tools. Frame it around the academic + WhatsApp angle: "Show HN: An open-source ML ordering tool for small greengrocers (LightGBM + PPO + WhatsApp)." Post on a Tuesday or Wednesday morning US Eastern time. One well-received Show HN can generate 500-2000 GitHub stars in 48 hours.

2. **arXiv or a blog post with the academic approach** — `academic/APPROACH.md` already cites 8 papers. Publishing a short technical post (on your blog or Dev.to) titled something like "Why we chose LightGBM + PPO over deep learning for a small produce vendor" is the kind of specific, non-salesy content that gets shared in ML communities. Link to the repo.

3. **GitHub topics** — Add `food-waste`, `demand-forecasting`, `inventory-optimization`, `perishable-goods`, `lightgbm`, `reinforcement-learning`, `fastapi` to the repo topics. The `food-demand-forecasting` topic currently has fewer than 50 repos; being discoverable there is easy.

**Medium effort:**

4. **Reddit:** `r/MachineLearning`, `r/reinforcementlearning`, `r/Python` — share the technical writeup, not a product pitch. The academic grounding and real-world domain are both strong hooks for ML Reddit.

5. **Israeli tech Slack communities and LinkedIn** — The Hebrew language support and Israeli merchant focus are genuine differentiators in the local tech community. Israeli food-tech ecosystem communities (e.g., FoodTech IL) may amplify.

6. **Too Good To Go / OLIO / Open Food Network** — None of these organizations expose public APIs or run developer partnership programs (confirmed by search: no official APIs found). However, reaching out to their engineering teams with a short email framing meshek-ml as complementary (supplier-side optimization vs. their consumer-side redistribution) could open co-promotion or research collaboration. Low cost, uncertain return.

**Academic / NGO partners:**

7. **Leket Israel** — Israel's largest food rescue organization. They publish annual reports quantifying food waste at the supplier/merchant level. They do not have open-source or API programs, but are a credible co-author or endorser for academic work on food waste reduction. A pilot ("meshek-ml reduced waste by X% for 5 greengrocers; Leket validates the methodology") would be a strong external credibility signal.

8. **UN FAO Technical Platform on Food Loss and Waste** — FAO maintains a global hub for food loss reduction tools. Registering meshek-ml there after a credible public release is low friction and provides legitimacy for academic/NGO outreach.

9. **Academic ML conferences** — NeurIPS Workshop on ML for the Developing World, ICLR Tiny Papers track, or AgriFood-Tech workshops are realistic targets for a short paper once real merchant data exists.

### What Would Make meshek-ml Genuinely Attention-Worthy

The project is special enough to attract attention if it can show:
- Actual merchant data (even 1-2 real greengrocers using it)
- Measured waste reduction (even approximate: "3 merchants, 12% average waste reduction over 30 days")
- The academic grounding is already published (the 8 papers + APPROACH.md are a credibility differentiator)

Without real merchant validation, it is an interesting research project. With even one real merchant and a before/after waste measurement, it becomes a story.

**Confidence on promotion:** MEDIUM. Growth tactics for developer tools are well-documented; the food-waste niche angle is genuine but harder to validate without real user data.

---

## "Looks Done But Isn't" Checklist

- [ ] **FastAPI `/recommend` endpoint:** Returns `200 OK` for new merchant with zero history — verify it returns a default recommendation with `recommendation_basis: "default"`, not a `0` prediction or a 500 error.
- [ ] **Model loading:** Restart the FastAPI server and time the first request — it should be no slower than the second request (model loaded at startup, not on first call).
- [ ] **Hebrew parsing:** Test with an actual WhatsApp copy-paste, not text typed in a code editor — verify NFC normalization handles it correctly.
- [ ] **Multi-merchant isolation:** Create two merchants, add sales data for Merchant A, query Merchant B's recommendation — verify Merchant B's response contains no data from Merchant A.
- [ ] **Schema separation:** Change an internal pipeline field name and verify no API test breaks.
- [ ] **meshek integration:** Call `/recommend` from meshek's Fastify backend and confirm the HTTP timeout and error handling are both exercised.
- [ ] **Lifespan events:** Verify models are loaded before the first request arrives (not lazily on first call).

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Event loop blocking discovered in production | MEDIUM | Switch endpoint from `async def` to `def`; deploy; no data migration needed |
| Schema coupling causes API breakage on pipeline change | HIGH | Add API versioning (`/v1/`); deprecate old endpoint; coordinate meshek app update |
| Cross-merchant data leakage discovered | HIGH | Audit all SQL queries; migrate to per-merchant file isolation; notify affected merchants |
| Hebrew parser fails silently at scale | LOW | Add logging first (no code change needed); then fix normalization; rebuild product dictionary |
| ML models not found on startup | LOW | FastAPI lifespan event fails fast; fix model path and redeploy |
| Cold-start returns nonsense recommendation | MEDIUM | Add three-tier fallback logic; existing merchant data is unaffected |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Event loop blocking | API foundation (Phase 1) | Load test with 10 concurrent requests; p99 < 2x p50 |
| Model loading on every request | API foundation (Phase 1) | Time first vs. second request after restart; delta < 50ms |
| No cold-start strategy | Recommendation engine (Phase 2) | Create new merchant; call `/recommend`; verify response has `recommendation_basis: "default"` |
| API/pipeline schema coupling | API foundation (Phase 1) | Rename an internal field; verify no API test fails |
| Cross-merchant data leakage | Sales history persistence (Phase 1) | Two-merchant integration test; verify response isolation |
| Hebrew parsing silent failure | Hebrew parsing (Phase 2) | Test corpus of 20 WhatsApp-sourced strings; verify parse rate > 85% |
| Feature engineering on full history | Sales history persistence | Time `/recommend` with 30 vs. 365 days of history; verify < 20% latency increase |

---

## Sources

- FastAPI event loop and async guidance: https://fastapi.tiangolo.com/async/
- FastAPI lifespan context: https://fastapi.tiangolo.com/advanced/events/
- ML model serving pitfalls: https://ambacia.eu/careers-post/why-your-ml-model-fails-in-production/
- FastAPI ML optimization: https://luis-sena.medium.com/how-to-optimize-fastapi-for-ml-model-serving-6f75fb9e040d
- Multi-tenant data isolation: https://medium.com/@justhamade/architecting-secure-multi-tenant-data-isolation-d8f36cb0d25e
- Open-core model overview: https://handbook.opencoreventures.com/how-we-work/open-core
- frePPLe (open-source supply chain): https://github.com/frePPLe/frepple
- tensor-house (supply chain RL): https://github.com/ikatsov/tensor-house
- GitHub demand-forecasting topic: https://github.com/topics/demand-forecasting
- GitHub food-demand-forecasting topic: https://github.com/topics/food-demand-forecasting
- Leket Israel food waste data: https://foodwastereport.leket.org/en/
- UN FAO food loss platform: https://www.fao.org/platform-food-loss-waste/en
- Open Food Network: https://github.com/openfoodfoundation/openfoodnetwork
- HN launch lessons: https://medium.com/@baristaGeek/lessons-launching-a-developer-tool-on-hacker-news-vs-product-hunt-and-other-channels-27be8784338b

---

*Pitfalls research for: open-source ML inference service for perishable inventory (meshek-ml v1.1)*
*Researched: 2026-04-10*
