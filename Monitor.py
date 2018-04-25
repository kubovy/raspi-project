#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import subprocess
import traceback
from threading import *
from ModuleMQTT import ModuleMQTT


class Check(object):
    def __init__(self, topic, command, qos=1, retain=True, interval=60):
        self.topic = topic
        self.command = command
        self.qos = qos
        self.retain = retain
        self.interval = interval


class Monitor(ModuleMQTT):
    timer_map = {}

    def __init__(self, client, service_name, debug=False):
        super(Monitor, self).__init__(client, service_name, "monitor", debug)
        self.checks = [
            Check("uptime", 'uptime -p | sed -E "s/up ([0-9]+) days?, ([0-9]+) hours?, ([0-9]+) minutes?/\\1:\\2:\\3:00/g"'),
            Check("users", 'uptime | sed -E "s/.*([0-9]+) users?.*/\\1/g"'),
            Check("storage_root_size", 'df | grep "% /$" | sed -E "s/[^0-9]+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)%.*/\\1/g"', interval=86400),
            Check("storage_root_used", 'df | grep "% /$" | sed -E "s/[^0-9]+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)%.*/\\2/g"', interval=3600),
            Check("storage_root_free", 'df | grep "% /$" | sed -E "s/[^0-9]+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)%.*/\\3/g"', interval=3600),
            Check("storage_root_percent", 'df | grep "% /$" | sed -E "s/[^0-9]+([0-9]+)\\s+([0-9]+)\s+([0-9]+)\\s+([0-9]+)%.*/\\4/g"', interval=3600),
            Check("cpu", 'expr $(top -b | head -n 5 | grep %Cpu | sed -E "s/.* ([0-9]+)[,.][0-9]+ us,\\s+([0-9]+)[,.][0-9]+ sy,\\s+ ([0-9]+)[,.][0-9]+ ni.*/\\1 + \\2 + \\3/g")'),
            Check("load1", 'uptime | sed -E "s/.*load average: ([0-9]+[,.][0-9]+)[,.]\\s*([0-9]+[,.][0-9]+)[,.]\\s*([0-9]+[,.][0-9]+)/\\1/g" | sed -E "s/([0-9]+)[,.]([0-9]+)/\\1.\\2/g"'),
            Check("load5", 'uptime | sed -E "s/.*load average: ([0-9]+[,.][0-9]+)[,.]\\s*([0-9]+[,.][0-9]+)[,.]\\s*([0-9]+[,.][0-9]+)/\\2/g"'),
            Check("load15", 'uptime | sed -E "s/.*load average: ([0-9]+[,.][0-9]+)[,.]\\s*([0-9]+[,.][0-9]+)[,.]\\s*([0-9]+[,.][0-9]+)/\\3/g" | sed -E "s/([0-9]+)[,.]([0-9]+)/\\1.\\2/g"'),
            Check("mem_total", 'free | grep Mem: | sed -E "s/Mem:\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+).*/\\1/g"'),
            Check("mem_used", 'free | grep Mem: | sed -E "s/Mem:\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+).*/\\2/g"'),
            Check("mem_free", 'free | grep Mem: | sed -E "s/Mem:\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+).*/\\3/g"'),
            Check("mem_shared", 'free | grep Mem: | sed -E "s/Mem:\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+).*/\\4/g"'),
            Check("mem_cache", 'free | grep Mem: | sed -E "s/Mem:\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+).*/\\5/g"'),
            Check("mem_available", 'free | grep Mem: | sed -E "s/Mem:\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+).*/\\6/g"'),
            Check("swap_total", 'free | grep Swap | sed -E "s/Swap:\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+).*/\\1/g"'),
            Check("swap_used", 'free | grep Swap | sed -E "s/Swap:\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+).*/\\2/g"'),
            Check("swap_free", 'free | grep Swap | sed -E "s/Swap:\\s+([0-9]+)\\s+([0-9]+)\\s+([0-9]+).*/\\3/g"')
        ]
        for check in self.checks:
            self.trigger(check)

    def trigger(self, check):
        self.logger.debug(check.topic + " triggered")
        try:
            result = subprocess.Popen(check.command,
                                      stdout=subprocess.PIPE,
                                      shell=True).communicate()[0].strip()
            self.publish(check.topic, result, check.qos, check.retain)
        except:
            self.logger.error("Unexpected Error!")
            traceback.print_exc()
        timer = Timer(check.interval, self.trigger, [check])
        self.timer_map[check.topic] = timer
        timer.start()

    def finalize(self):
        for key in self.timer_map.keys():
            self.logger.debug("Timer " + key + " = " + str(self.timer_map[key]))
            if self.timer_map[key] is not None: self.timer_map[key].cancel()

