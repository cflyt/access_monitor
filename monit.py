#!/usr/bin/env python
#-*- coding: utf-8 -*-

import sys
import os
import time
import traceback
import optparse
from datetime import date, datetime
import logging
import logging.config

from core import pygtail
from core import util
from config import setting as sfg
from core.daemon import Daemon

current_dir = os.getcwd()
log_dir = current_dir + "/var/log"
run_dir = current_dir + "/var/run"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
if not os.path.exists(run_dir):
    os.makedirs(run_dir)

logging.config.dictConfig(sfg.LOGGING)

def _run(options):

    ######## file lock ########
    file_lock = util.FileLock("var/run/monitor.lock")
    if not file_lock.lock():
        print "Monitor is running"
        sys.exit(1)

    pattern = util.build_pattern(sfg.LOG_FORMAT)
    config_file = options.config_file
    alert_status_config_file, response_range_config_file, response_ratio_config_file, request_ratio_config_file = util.parse_config(config_file)

    while True:
        count = 0
        sys.stdout.flush()
        if not options.continue_read and not options.loop_run:
            fp = open(options.access_log, "r")
        else:
            fp = pygtail.Pygtail(options.access_log, offset_file="var/run/access_log.offset")

        if fp is not None:
            for line in fp:
                try:
                    count = count + 1
                    record = util.parse_log(line, pattern)
                    if record is None:
                        continue
                    util.alert_status(record, alert_status_config_file)
                    util.alert_response_time_range(record, response_range_config_file)
                    util.alert_response_time_ratio(record, response_ratio_config_file)
                    util.alert_request_time_ratio(record, request_ratio_config_file)
                except Exception, ex:
                    logging.error("monitor exception: %s" % traceback.format_exc())
        if not options.loop_run:
            break
        if count < 1000:
            time.sleep(1)
        elif count < 10:
            time.sleep(5)


class MDaemon(Daemon):
    def run(self):
        _run(self.options)


def main():
    usage = "usage: %prog [OPTION]"

    option_list = (
        optparse.make_option("-l", "--access-log", dest="access_log",
            help="Specify access log file path. "),
        optparse.make_option("-f", "--config-file", dest="config_file",
            help="Specify config file path. "),
        optparse.make_option("-c", "--continue-read", dest="continue_read", action="store_true",
            help="When using continue_run, this script will read the log from last position "
        ),
        optparse.make_option("--loop", dest="loop_run", action="store_true",
            help="run in loop, read from last postion"
        ),
        optparse.make_option("-s", dest="start_op", action="store",
            help="this script will run as daemon"
        ),
    )
    option_default = {
    }

    parser = optparse.OptionParser(usage=usage, option_list=option_list)
    parser.set_defaults(**option_default)
    options, args = parser.parse_args()
    if options.access_log is None:
        parser.error("you must specify access_log.")

    if not os.path.isfile(options.access_log):
        parser.error("access_log %s not exist." % options.access_log)

    if options.config_file is None:
        parser.error("you must specify config_file.")

    if not os.path.isfile(options.config_file):
        parser.error("config_file %s not exist." % options.config_file)

    if options.start_op is None:
        _run(options)
    else:
        daemon = MDaemon(current_dir + '/var/run/monit.pid',
                stdin= "/dev/null",
                stdout=current_dir + "/var/log/err.log",
                stderr=current_dir + "/var/log/err.log",
                options=options)
        if options.start_op == "start":
            daemon.start()
        elif options.start_op == "stop":
            daemon.stop()
        elif options.start_op == "restart":
            daemon.restart()


if __name__ == "__main__":
    main()
