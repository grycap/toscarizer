#!/bin/sh
/opt/telegraf/bin/telegraf  --config /opt/telegraf/telegraf.conf &
supervisor
