.PHONY: install lint typecheck test check demo clean

install:
	python -m pip install -e ".[dev]"

lint:
	ruff check src tests scripts
	ruff format --check src tests scripts

typecheck:
	mypy src

test:
	pytest --cov=anomaly_pipeline --cov-report=term-missing

check: lint typecheck test

demo:
	python -m anomaly_pipeline train --history data/sample/historical_metrics.csv --config config/claims.yml --model artifacts/isolation_forest.joblib
	python -m anomaly_pipeline detect --input data/sample/claims_current.csv --history data/sample/historical_metrics.csv --model artifacts/isolation_forest.joblib --config config/claims.yml --store data/anomalies.db --as-of 2026-09-22T12:00:00Z

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage artifacts/*.joblib data/*.db
