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
    def __init__(self, topic, command, qos=1, retain=False, interval=60):
        self.topic = topic
        self.command = command
        self.qos = qos
        self.retain = retain
        self.interval = interval


class RPI(ModuleMQTT):
    timer_map = {}

    def __init__(self, client, service_name, debug=False):
        super(RPI, self).__init__(client, service_name, "rpi", debug)
        self.checks = [
            Check("cpu_temp", '/opt/vc/bin/vcgencmd measure_temp | sed -E "s/temp=([0-9]+\\.[0-9]+)\'C/\\1/g"'),
            Check("arm_freq", '/opt/vc/bin/vcgencmd measure_clock arm | cut -d"=" -f2', interval=3600),
            Check("core_freq", '/opt/vc/bin/vcgencmd measure_clock core | cut -d"=" -f2', interval=3600),
            Check("h264_freq", '/opt/vc/bin/vcgencmd measure_clock h264 | cut -d"=" -f2', interval=3600),
            Check("isp_freq", '/opt/vc/bin/vcgencmd measure_clock isp | cut -d"=" -f2', interval=3600),
            Check("v3d_freq", '/opt/vc/bin/vcgencmd measure_clock v3d | cut -d"=" -f2', interval=3600),
            Check("uart_freq", '/opt/vc/bin/vcgencmd measure_clock uart | cut -d"=" -f2', interval=3600),
            Check("pwm_freq", '/opt/vc/bin/vcgencmd measure_clock pwm | cut -d"=" -f2', interval=3600),
            Check("emmc_freq", '/opt/vc/bin/vcgencmd measure_clock emmc | cut -d"=" -f2', interval=3600),
            Check("pixel_freq", '/opt/vc/bin/vcgencmd measure_clock pixel | cut -d"=" -f2', interval=3600),
            Check("vec_freq", '/opt/vc/bin/vcgencmd measure_clock vec | cut -d"=" -f2', interval=3600),
            Check("hdmi_freq", '/opt/vc/bin/vcgencmd measure_clock hdmi | cut -d"=" -f2', interval=3600),
            Check("dpi_freq", '/opt/vc/bin/vcgencmd measure_clock dpi | cut -d"=" -f2', interval=3600),
            Check("core_volt", "/opt/vc/bin/vcgencmd measure_volts core | sed -E 's/volt=([0-9]+\.[0-9]+)V/\\1/g'"),
            Check("sdram_c_volt", "/opt/vc/bin/vcgencmd measure_volts sdram_c | sed -E 's/volt=([0-9]+\.[0-9]+)V/\\1/g'"),
            Check("sdram_i_volt", "/opt/vc/bin/vcgencmd measure_volts sdram_i | sed -E 's/volt=([0-9]+\.[0-9]+)V/\\1/g'"),
            Check("sdram_p_volt", "/opt/vc/bin/vcgencmd measure_volts sdram_p | sed -E 's/volt=([0-9]+\.[0-9]+)V/\\1/g'"),
            Check("arm_mem", '/opt/vc/bin/vcgencmd get_mem arm | cut -d"=" -f2 | sed -E "s/([0-9]+).*/\\1/g"'),
            Check("gpu_mem", '/opt/vc/bin/vcgencmd get_mem gpu | cut -d"=" -f2 | sed -E "s/([0-9]+).*/\\1/g"')
        ]
        for check in self.checks:
            self.trigger(check)

    def trigger(self, check):
        global timer_map
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
