#!/bin/sh
PATH=/bin:/usr/bin:/sbin:/usr/sbin
HOME=/root
USER=root
LOGNAME=root
SHELL=/bin/sh
TERM=vt100
LANG=C
TZ=UTC0
PS1='\h:\w \u\$ '
export PATH HOME USER LOGNAME SHELL TERM LANG TZ PS1
cat /etc/motd
exec /bin/sh -i
