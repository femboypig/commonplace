.DEFAULT_GOAL := help
PYTHON ?= python3
JOBS ?= 2

.PHONY: help fetch doctor tools runtime check-tools xnu-headers check-xnu-host kernel check-kernel test
help:
	@printf '%s\n' 'commonplace — darwin/x86_64' \
	  'make doctor       check host tools and virtualization' \
	  'make fetch        fetch and verify pinned upstream sources' \
	  'make tools        build local darwin cross-development tools' \
	  'make runtime      build kernel profile buffer runtime' \
	  'make check-tools  test mach-o linking and mach interface generation' \
	  'make xnu-headers  export apple kernel headers using linux host tools' \
	  'make check-xnu-host  verify header exports and atomic installation' \
	  'make kernel       build and validate the development kernel' \
	  'make check-kernel validate the existing kernel artifact' \
	  'make test         run source acquisition tests'

fetch:
	$(PYTHON) scripts/fetch.py

doctor:
	$(PYTHON) scripts/doctor.py

tools: fetch
	JOBS=$(JOBS) bash scripts/build-tools.sh

runtime: fetch
	bash scripts/build-runtime.sh

check-tools:
	$(PYTHON) scripts/check-tools.py

xnu-headers: fetch
	$(PYTHON) scripts/build-xnu.py exporthdrs

check-xnu-host:
	$(PYTHON) scripts/check-xnu-host.py

kernel: runtime
	$(PYTHON) scripts/build-xnu.py all
	$(PYTHON) scripts/check-kernel.py

check-kernel:
	$(PYTHON) scripts/check-kernel.py

test:
	$(PYTHON) -m unittest discover -s tests -v
