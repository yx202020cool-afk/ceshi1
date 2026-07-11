.PHONY: init demo test lint typecheck check api web scheduler backtest clean

init:
	python -m ashare_replay.cli init-db

demo:
	python -m ashare_replay.cli generate-all --date today

test:
	python -m pytest

lint:
	python -m ruff check .

typecheck:
	python -m mypy ashare_replay

check: lint typecheck test

api:
	uvicorn ashare_replay.api:app --host 127.0.0.1 --port 8000

web:
	streamlit run ashare_replay/ui/streamlit_app.py --server.port 8501

scheduler:
	python -m ashare_replay.cli scheduler

backtest:
	python -m ashare_replay.cli backtest --start 2026-07-01 --end 2026-07-10

clean:
	python -m ashare_replay.cli clean-cache
