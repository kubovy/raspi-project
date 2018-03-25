#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
from Logger import Logger


class Module(object):

    def __init__(self, debug=False):
        self.logger = Logger(type(self).__name__, debug)

    def finalize(self):
        pass
