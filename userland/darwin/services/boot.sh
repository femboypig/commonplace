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
if ! /usr/libexec/commonplace/register-network; then
    echo 'commonplace: network interface registration failed' >&2
fi
if ! ifconfig lo0 inet 127.0.0.1 netmask 255.0.0.0 up; then
    echo 'commonplace: loopback configuration failed' >&2
fi
: > /var/run/commonplace.ready
for script in /etc/rc /data/rc; do
    if [ -f "$script" ] && [ -r "$script" ]; then
        /bin/sh "$script"
    fi
done
