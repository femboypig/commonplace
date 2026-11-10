.DEFAULT_GOAL := help
PYTHON ?= python3
JOBS ?= 2

.PHONY: help fetch doctor tools check-tools test
help:
	@printf '%s\n' 'commonplace — darwin/x86_64' \
	  'make doctor       check host tools and virtualization' \
	  'make fetch        fetch and verify pinned upstream sources' \
	  'make tools        build local darwin cross-development tools' \
	  'make check-tools  test mach-o linking and mach interface generation' \
	  'make test         run source acquisition tests'

fetch:
	$(PYTHON) scripts/fetch.py

doctor:
	$(PYTHON) scripts/doctor.py

tools: fetch
	JOBS=$(JOBS) bash scripts/build-tools.sh

check-tools:
	$(PYTHON) scripts/check-tools.py

test:
	$(PYTHON) -m unittest discover -s tests -v
