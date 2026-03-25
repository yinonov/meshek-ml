.PHONY: install install-all lint format test test-all sim forecast optimize federate demo clean publish-model publish-data tracking-dashboard

install:
	pip install -e ".[dev,simulation]"

install-all:
	pip install -e ".[all]"

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff check --fix src/ tests/
	ruff format src/ tests/

test:
	pytest -m "not slow" tests/

test-all:
	pytest tests/

sim:
	python scripts/run_simulation.py

forecast:
	python scripts/run_forecast.py

optimize:
	python scripts/run_optimization.py

federate:
	python scripts/run_federated.py

demo:
	streamlit run src/meshek_ml/demo/dashboard.py

clean:
	rm -rf outputs/ multirun/ .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +

# ── HF Hub publishing ──────────────────────────────────────────────
publish-data:
	hf upload meshek-ml/perishable-demand data/synthetic/ --repo-type dataset

publish-model:
	@echo "Usage: make publish-model MODEL=models/ppo_inventory.zip"
	@test -n "$(MODEL)" || (echo "ERROR: set MODEL=path/to/model" && exit 1)
	hf upload meshek-ml/inventory-models $(MODEL)

# ── Experiment tracking ────────────────────────────────────────────
tracking-dashboard:
	trackio show
