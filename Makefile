# CiteSure - make targets (documented interface).
# Windows note: this machine has no `make`; every target below is a thin wrapper
# over the equivalent `python -m ...` command, which always works directly.

PY ?= python

.PHONY: help download ingest serve eval eval-compare test lint clean

help:
	@echo "Targets: download ingest serve eval eval-compare test lint clean"
	@echo "No make? Run the underlying commands, e.g. $(PY) -m citesure.eval.run"

download:
	$(PY) scripts/download_corpus.py

ingest:
	$(PY) -m citesure.ingest.cli all

serve:
	$(PY) -m uvicorn citesure.app:app --host 127.0.0.1 --port 8000

eval:
	$(PY) -m citesure.eval.run

eval-compare:
	$(PY) -m citesure.eval.compare

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check citesure tests scripts

clean:
	@echo "Removing generated index/ and caches (keeps data/raw PDFs)"
	rm -rf index/* .pytest_cache
