NAME = fly-in

PYTHON = uv run python

.PHONY: install run run-verbose run-visual debug clean lint

install:
	uv sync

run:
	$(PYTHON) -m src

run-verbose:
	$(PYTHON) -m src --verbose

run-visual:
	$(PYTHON) -m src --visual

debug:
	$(PYTHON) -m pdb -m src

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	find . -type d -name "*.egg-info" -exec rm -rf {} +

lint:
	$(PYTHON) -m flake8 src
	$(PYTHON) -m mypy src