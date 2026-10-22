# Thin wrapper: every target calls tools/build.py, so it behaves the same on Windows, Linux and macOS
# (no Unix-only shell commands in here). A bare `make` only explains the targets; `make all` builds.
# Needs: python and `pip install ziglang`. Without make: python tools/build.py [target]
ifeq ($(OS),Windows_NT)
PYTHON ?= python
else
PYTHON ?= python3
endif

help:
	$(PYTHON) tools/build.py help

all windows linux icons desktop clean:
	$(PYTHON) tools/build.py $@

.PHONY: help all windows linux icons desktop clean
