#!/usr/bin/env python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import prctl
from os.path import dirname

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from Logger import Logger


def observe(path, listener, logger=None):
    """Creates an observer to the provided path

    :param listener: no-arg method called when change (creation/modification) happens to the file
    :param logger: optional logger. A new will be created if none is provided.
    """
    observer = None
    if path is not None:
        observer = Observer()
        event_handler = __FileWatcherHandler(path, listener, logger)  # create event handler
        observer.schedule(event_handler, path=dirname(path))
        observer.daemon = True
        observer.start()
    return observer


class __FileWatcherHandler(FileSystemEventHandler):

    def __init__(self, path, listener, logger=None, debug=False):
        super(FileSystemEventHandler, self).__init__()
        self.path = path
        self.listener = listener
        self.logger = Logger(type(self).__name__, debug) if logger is None else logger
        prctl.set_name("File Watcher")

    def on_created(self, event):  # when file is created
        if event.src_path == self.path:
            self.logger.debug(event.src_path + " created")
            self.listener()

    def on_modified(self, event):
        if event.src_path == self.path:
            self.logger.debug(event.src_path + " modified")
            self.listener()
