.DEFAULT_GOAL := help
PYTHON ?= python3
JOBS ?= 2

.PHONY: help fetch doctor tools runtime crypto check-tools xnu-headers check-xnu-host kernel check-kernel loader boot boot-bsd boot-checks rootfs-tools userland rootfs boot-init boot-console test
help:
	@printf '%s\n' 'commonplace — darwin/x86_64' \
	  'make doctor       check host tools and virtualization' \
	  'make fetch        fetch and verify pinned upstream sources' \
	  'make tools        build local darwin cross-development tools' \
	  'make runtime      build kernel profile buffer runtime' \
	  'make crypto       build freestanding kernel crypto primitives' \
	  'make check-tools  test mach-o linking and mach interface generation' \
	  'make xnu-headers  export apple kernel headers using linux host tools' \
	  'make check-xnu-host  verify header exports and atomic installation' \
	  'make kernel       build and validate the development kernel' \
	  'make check-kernel validate the existing kernel artifact' \
	  'make loader       build the multiboot darwin loader' \
	  'make boot         observe a bounded qemu boot and save diagnostics' \
	  'make boot-bsd     require BSD to reach root device discovery' \
	  'make boot-checks  repeat early boots with 512, 1024 and 2048 MiB' \
	  'make rootfs       build the bootstrap init and HFS+ root image' \
	  'make boot-init    require PID 1 and exercise the serial console' \
	  'make boot-console attach this terminal to the guest (Ctrl-A X exits)' \
	  'make test         run targeted regression tests'

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

crypto: fetch
	bash scripts/build-crypto.sh

kernel: runtime crypto
	$(PYTHON) scripts/build-xnu.py all
	$(PYTHON) scripts/check-kernel.py

check-kernel:
	$(PYTHON) scripts/check-kernel.py

loader:
	bash scripts/build-loader.sh

boot: loader check-kernel
	$(PYTHON) scripts/boot-qemu.py

boot-bsd: loader check-kernel
	$(PYTHON) scripts/boot-qemu.py --seconds 150 --require-root-wait

boot-checks: loader check-kernel
	$(PYTHON) scripts/check-boots.py

rootfs-tools: fetch
	bash scripts/build-rootfs-tools.sh

userland: fetch
	$(PYTHON) scripts/build-userland.py

rootfs: userland rootfs-tools
	$(PYTHON) scripts/build-rootfs.py

boot-init: loader check-kernel rootfs
	$(PYTHON) scripts/boot-qemu.py --seconds 150 --root-image build/rootfs/root.hfs --check-console

boot-console: loader check-kernel rootfs
	$(PYTHON) scripts/console-qemu.py

test:
	$(PYTHON) -m unittest discover -s tests -v
