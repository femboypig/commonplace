.DEFAULT_GOAL := help
PYTHON ?= python3
JOBS ?= 2

.PHONY: check-maintenance-failures check-recovery check-service-update check-login package-services darwin-services service-image boot-services check-launchd help fetch doctor tools runtime crypto check-tools xnu-headers check-xnu-host kernel check-kernel loader boot boot-bsd boot-checks rootfs-tools darwin-sdk darwin-libraries darwin-userland check-darwin check-darwin-runtime check-dispatch check-foundation check-corefoundation check-service-runtime userland rootfs boot-init boot-console boot-recovery system-disk check-system check-hfs check-mount check-newfs check-admin-runtime update-system check-update disk-image check-storage check-storage-reliability package test
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
	  'make rootfs       build Darwin commands, bash and the HFS+ root image' \
	  'make check-darwin validate the native C runtime and command suite in QEMU' \
	  'make check-darwin-runtime validate dyld, malloc and pthreads in QEMU' \
	  'make check-dispatch verify native queues, timers and asynchronous IO' \
	  'make check-foundation verify native math and ICU Unicode APIs' \
	  'make check-corefoundation verify native property lists, streams and run loops' \
	  'make check-service-runtime verify native ASL records and Mach notifications' \
	  'make service-image build the native Apple launchd system on a separate disk' \
	  'make boot-services boot Apple launchd, notifyd and syslogd' \
	  'make check-login verify password provisioning and native user sessions' \
	  'make check-launchd verify native services and persistent system logging' \
	  'make boot-init    require PID 1 and exercise the serial console' \
	  'make boot-console attach this terminal to the guest (Ctrl-A X exits)' \
	  'make boot-recovery boot the RAM recovery root' \
	  'make system-disk  install the persistent system disk once' \
	  'make check-system verify persistent root and recovery boots' \
	  'make update-system update the offline system and keep a rollback image' \
	  'make check-update verify updates and rollback in QEMU' \
	  'make check-service-update verify service updates with preserved users' \
	  'make check-recovery verify password recovery and HFS+ crash repair' \
	  'make check-maintenance-failures verify interrupted and rejected operations' \
	  'make check-hfs    verify native HFS checking and repair' \
	  'make check-mount  verify native Apple mount and unmount commands' \
	  'make check-newfs  verify native HFS formatting and normalization' \
	  'make check-admin-runtime verify local accounts, PAM and syslog APIs' \
	  'make disk-image   create the persistent data disk without replacing it' \
	  'make check-storage verify persistence across poweroff and reboot' \
	  'make check-storage-reliability verify crash recovery and full disks' \
	  'make package-services package the native Apple service system' \
	  'make package      package a ready-to-run QEMU system' \
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

darwin-sdk: fetch
	$(PYTHON) scripts/build-xnu.py exporthdrs
	$(PYTHON) scripts/build-darwin-sdk.py

darwin-libraries: darwin-sdk
	$(PYTHON) scripts/build-libsyscall.py
	$(PYTHON) scripts/build-darwin-mach.py
	$(PYTHON) scripts/build-darwin-platform.py
	$(PYTHON) scripts/build-darwin-pthread.py
	$(PYTHON) scripts/build-darwin-malloc.py
	$(PYTHON) scripts/build-darwin-cxx.py
	$(PYTHON) scripts/build-darwin-math.py
	$(PYTHON) scripts/build-darwin-libc.py
	$(PYTHON) scripts/build-darwin-libinfo.py
	$(PYTHON) scripts/build-darwin-file-libraries.py
	$(PYTHON) scripts/build-darwin-dyld.py
	$(PYTHON) scripts/build-darwin-kernel-library.py
	$(PYTHON) scripts/build-darwin-dispatch.py
	$(PYTHON) scripts/build-darwin-bootstrap.py
	$(PYTHON) scripts/build-darwin-launch.py
	$(PYTHON) scripts/build-darwin-notify.py
	$(PYTHON) scripts/build-darwin-diagnostics.py
	$(PYTHON) scripts/build-darwin-asl.py
	$(PYTHON) scripts/build-darwin-macho.py
	$(PYTHON) scripts/build-darwin-system.py

darwin-userland: darwin-libraries
	$(PYTHON) scripts/build-darwin-icu.py
	$(PYTHON) scripts/build-darwin-cf.py
	$(PYTHON) scripts/build-darwin-crypto.py
	$(PYTHON) scripts/build-darwin-password.py
	$(PYTHON) scripts/build-darwin-pam.py
	$(PYTHON) scripts/build-darwin-accounts.py
	$(PYTHON) scripts/build-darwin-login.py
	$(PYTHON) scripts/build-darwin-newfs.py
	$(PYTHON) scripts/build-darwin-commands.py
	$(PYTHON) scripts/build-darwin-bash.py

# These targets use Apple's published service manager and isolated system image.
darwin-services: userland
	$(PYTHON) scripts/build-darwin-bsm.py
	$(PYTHON) scripts/build-darwin-iokit.py
	$(PYTHON) scripts/build-darwin-dnssd.py
	$(PYTHON) scripts/build-darwin-readline.py
	$(PYTHON) scripts/build-darwin-launchd.py
	$(PYTHON) scripts/build-darwin-launchctl.py
	$(PYTHON) scripts/build-darwin-notifyd.py
	$(PYTHON) scripts/build-darwin-syslogd.py

service-image: darwin-services rootfs-tools
	$(PYTHON) scripts/create-service-image.py

boot-services: loader check-kernel service-image disk-image
	$(PYTHON) scripts/console-qemu.py --system-disk build/disks/services.hfs

check-login: loader check-kernel darwin-services rootfs-tools
	$(PYTHON) scripts/check-login.py

check-launchd: loader check-kernel darwin-services rootfs-tools
	$(PYTHON) scripts/check-launchd.py


userland: darwin-userland
	$(PYTHON) scripts/build-userland.py

rootfs: userland rootfs-tools
	$(PYTHON) scripts/build-rootfs.py

boot-init: loader check-kernel rootfs
	$(PYTHON) scripts/boot-qemu.py --seconds 150 --root-image build/rootfs/root.hfs --check-console

disk-image: rootfs-tools
	$(PYTHON) scripts/create-disk.py

system-disk: userland rootfs-tools
	$(PYTHON) scripts/create-system-disk.py

boot-recovery: loader check-kernel rootfs disk-image
	$(PYTHON) scripts/console-qemu.py --recovery

update-system: loader check-kernel darwin-services rootfs
	$(PYTHON) scripts/update-system.py

check-update: loader check-kernel darwin-services rootfs
	$(PYTHON) scripts/check-update.py

check-service-update: loader check-kernel darwin-services rootfs
	$(PYTHON) scripts/check-service-update.py

check-recovery: loader check-kernel darwin-services rootfs
	$(PYTHON) scripts/check-recovery.py

check-maintenance-failures: loader check-kernel darwin-services rootfs
	$(PYTHON) scripts/check-maintenance-failures.py

check-hfs: loader check-kernel rootfs
	$(PYTHON) scripts/check-hfs.py

check-mount: loader check-kernel rootfs
	$(PYTHON) scripts/check-mount.py

check-newfs: loader check-kernel rootfs
	$(PYTHON) scripts/check-newfs.py

check-admin-runtime: loader check-kernel rootfs
	$(PYTHON) scripts/check-admin-runtime.py

check-system: loader check-kernel rootfs
	$(PYTHON) scripts/check-system-disk.py

boot-console: loader check-kernel rootfs disk-image system-disk
	$(PYTHON) scripts/console-qemu.py

check-darwin: loader check-kernel rootfs
	$(PYTHON) scripts/check-darwin.py

check-darwin-runtime: loader check-kernel rootfs
	$(PYTHON) scripts/check-darwin-runtime.py

check-corefoundation: loader check-kernel rootfs
	$(PYTHON) scripts/check-corefoundation.py

check-service-runtime: loader check-kernel rootfs
	$(PYTHON) scripts/check-service-runtime.py

check-foundation: loader check-kernel rootfs
	$(PYTHON) scripts/check-foundation.py

check-dispatch: loader check-kernel rootfs
	$(PYTHON) scripts/check-dispatch.py

check-storage: loader check-kernel rootfs
	$(PYTHON) scripts/check-storage.py

check-storage-reliability: loader check-kernel rootfs
	$(PYTHON) scripts/check-storage-reliability.py

package-services: loader check-kernel rootfs darwin-services
	$(PYTHON) scripts/package-qemu.py --services

package: loader check-kernel rootfs
	$(PYTHON) scripts/package-qemu.py

test:
	$(PYTHON) -m unittest discover -s tests -v
