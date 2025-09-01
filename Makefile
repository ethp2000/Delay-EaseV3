.PHONY: lint format import

TARGETS = src main.py

lint:
	poetry run ruff check $(TARGETS)
	poetry run black --check $(TARGETS)
	poetry run isort --check-only $(TARGETS)

format:
	poetry run isort $(TARGETS)
	poetry run black $(TARGETS)
	poetry run ruff check --fix $(TARGETS)

import:
	PYTHONPATH=src poetry run python -c "import delay_ease as m; print(getattr(m,'__version__','ok'))"
