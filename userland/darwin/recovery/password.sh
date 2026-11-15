#!/bin/sh
set -eu
user=${1:?account name required}
mounted=no
finish()
{
    status=$?
    trap - EXIT
    if [ "$mounted" = yes ]; then
        sync
        umount /tmp/system || status=1
    fi
    if [ "$status" = 0 ]; then
        fsck_hfs -fn -c 16m /dev/rcp1 || status=1
    fi
    printf 'password-recovery-status:%s\n' "$status"
    poweroff
}
trap finish EXIT
fsck_hfs -fn -c 16m /dev/rcp1
mkdir /tmp/system
mount -t hfs /dev/cp1 /tmp/system
mounted=yes
test ! -L /tmp/system/etc
test -d /tmp/system/etc
passwd -i file -l /tmp/system/etc/master.passwd -- "$user"
