#!/bin/sh
PATH=/bin:/usr/bin:/sbin:/usr/sbin
export PATH
if [ -r /etc/hostname ]; then
    IFS= read -r name < /etc/hostname
    hostname "$name"
fi
if [ -b /dev/cp0 ]; then
    mount -t hfs /dev/cp0 /data
fi
: > /var/run/commonplace.ready
for script in /etc/rc /data/rc; do
    if [ -f "$script" ] && [ -r "$script" ]; then
        /bin/sh "$script"
    fi
done
