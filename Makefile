VENV=.venv
PY=$(VENV)/Scripts/python

.PHONY: venv install test cleanup map embed all

venv:
	python -m venv $(VENV)

install: venv
	$(PY) -m pip install -U pip
	$(PY) -m pip install -r requirements.txt || true
	$(PY) -m pip install pytest

test: install
	$(PY) -m pytest -q

cleanup:
	$(PY) run_cleanup.py

map:
	$(PY) aggressive_template_map_and_writeback.py

embed: install
	$(PY) embed_memory.py

all: cleanup map test embed
