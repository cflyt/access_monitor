#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    common utilities
"""

import os
import fcntl
import cPickle as pickle
import re
import functools
import ConfigParser
import socket
import time
import logging

from config import setting as sfg
from cache import ExpiringDict
import send_alarm

g_cache_engine = ExpiringDict(100)

def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()

    return ip

g_host_ip = get_host_ip()

############# MONITOR FIELD RELATED ###############

def to_int(value, default_value=0):
    return int(value) if value and value != '-' else default_value

def to_float(value, default_value=0.0):
    return float(value) if value and value != '-' else default_value

def to_status(value, default_value="200"):
    value = value if value and value != '-' else default_value
    return value[0] + "xx"


FIELDS_HANDLERS = {
    "requests": functools.partial(to_int, default_value=1),
    "status": None,
    "body_bytes_sent": to_int,
    "request_time": to_float,
    "upstream_response_time": to_float,
    "upstream_response_length": to_int,
    "request_length": to_int,
    "bytes_sent": to_int,
}

def etl_field(field, record):
    field_value = "-"
    if field in sfg.LOG_FIELDS:
        field_value = record.get(field, "-")

    field_handler = FIELDS_HANDLERS[field]
    if field_handler is not None:
        field_value = field_handler(field_value)

    return field_value

############### COMMON TOOLS ################

def build_pattern(log_format):
    pattern = re.sub(sfg.REGEX_SPECIAL_CHARS, r'\\\1', log_format)
    pattern = re.sub(sfg.REGEX_LOG_FORMAT_VARIABLE, '(?P<\\1>.*)', pattern)
    return re.compile(pattern)


def parse_log(line, pattern):
    m = pattern.match(line)

    # nginx access_log not match monitor LOG_FORMAT
    if m is None:
        return None

    record = m.groupdict()
    return record


class Serializer(object):
    """
    A tool for serialize/unserialize object
    """
    @classmethod
    def to_string(cls, obj):
        """
        Serialize a object into string
        """
        return pickle.dumps(obj)

    @classmethod
    def to_object(cls, string):
        """
        Unserialize a string into object

        >>> from base.util import Serializer
        >>>
        >>> obj_str = "xxxxxx"
        >>> obj = Serializer.to_object(obj_string)
        """
        return pickle.loads(string)


class FileLock(object):
    def __init__(self, lock_file):
        self._file = lock_file
        self._fd = None
        self._locked = False

    def lock(self):
        if self._locked:
            return True

        fd = open(self._file, 'a+b')
        try:
            fcntl.flock(fd.fileno(), fcntl.LOCK_NB | fcntl.LOCK_EX)
        except IOError:
            fd.close()
            return False

        self._fd = fd
        self._locked = True
        return True

    def release(self):
        if self._locked:
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
            self._fd.close()
            self._fd = None
            self._locked = False

    def get_data(self):
        if not self._locked:
            return None

        self._fd.seek(0)
        data = self._fd.read()
        if len(data) < 1:
            return None

        return Serializer.to_object(data)

    def set_data(self, data):
        if not self._locked:
            return

        self._fd.truncate(0)
        self._fd.write(Serializer.to_string(data))
        self._fd.flush()

    def __del__(self):
        self.release()


#######################  ALERT RELATED  #######################
def alert_print(key, message):
    print message

def alert_sms(key, message):
    send_alarm.sendsms(message, sfg.ALERT_MOBILES)

def alert_weihui(key, message):
    send_alarm.sendweihui2(message, gid=sfg.WEIHUI_ALARM_TYPE)

def alert_mail(key, message):
    send_alarm.send_mail("fdfs monitor 报警", message, sfg.ALERT_EMAILS)


ALERT_METHOD_HANDLERS = {
    "print": alert_print,
    "sms": alert_sms,
    "weihui": alert_weihui,
    "mail": alert_mail,
}

def get_alert_status_config(config_file):
    config = {}
    conf = ConfigParser.ConfigParser()
    conf.read(config_file)

    for section in conf.sections():
        if conf.get(section, "type") != "status":
            continue

        target_status = conf.get(section, "target")
        config[target_status] = {}
        config[target_status].update(
            alert_threshold = int(conf.get(section, "threshold")),
            alert_time_range = int(conf.get(section, "time_range")),
            alert_method_list = map(lambda x: str(x.strip()), conf.get(section, "alert").split(",")),
        )

        if "request_time_threshold" in conf.options(section):
            config[target_status].update(request_time_threshold = float(conf.get(section, "request_time_threshold")))

    return config


def get_alert_response_range_config(config_file):
    config = {}
    conf = ConfigParser.ConfigParser()
    conf.read(config_file)

    for section in conf.sections():
        if conf.get(section, "type") != "response_range":
            continue

        config.update(
            alert_threshold = int(conf.get(section, "threshold")),
            alert_time_range = int(conf.get(section, "time_range")),
            alert_method_list = map(lambda x: str(x.strip()), conf.get(section, "alert").split(",")),
            request_length_range = map(lambda x: int(x.strip()), conf.get(section, "request_length_range").split(",")),
            warning_line = float(conf.get(section, "warning_line"))
        )

    return config


def get_alert_response_ratio_config(config_file):
    config = {}
    conf = ConfigParser.ConfigParser()
    conf.read(config_file)

    for section in conf.sections():
        if conf.get(section, "type") != "response_ratio":
            continue

        config.update(
            alert_threshold = int(conf.get(section, "threshold")),
            alert_time_range = int(conf.get(section, "time_range")),
            alert_method_list = map(lambda x: str(x.strip()), conf.get(section, "alert").split(",")),
            warning_line = float(conf.get(section, "warning_line")),
            response_time_threshold = float(conf.get(section, "response_time_threshold"))
        )

    return config

def get_alert_request_ratio_config(config_file):
    config = {}
    conf = ConfigParser.ConfigParser()
    conf.read(config_file)

    for section in conf.sections():
        if conf.get(section, "type") != "request_ratio":
            continue

        config.update(
            alert_threshold = int(conf.get(section, "threshold")),
            alert_time_range = int(conf.get(section, "time_range")),
            alert_method_list = map(lambda x: str(x.strip()), conf.get(section, "alert").split(",")),
            ratio_warning_line = float(conf.get(section, "ratio_warning_line", 512)),
            body_sent_byte_warning_line = float(conf.get(section, "body_sent_byte_warning_line", 512)),
            request_time_threshold = float(conf.get(section, "request_time_threshold"))
        )

    return config


def parse_config(config_file):
    alert_config_file = get_alert_status_config(config_file)
    response_range_config_file = get_alert_response_range_config(config_file)
    response_ratio_config_file = get_alert_response_ratio_config(config_file)
    request_ratio_config_file = get_alert_request_ratio_config(config_file)

    return alert_config_file, response_range_config_file, response_ratio_config_file, request_ratio_config_file


def alert_status(record, config_file):
    if len(config_file) == 0:
        return

    status = etl_field("status", record)

    config = config_file.get(status)
    if config is None:
        return

    if "request_time_threshold" in config:
        request_time = etl_field("request_time", record)
        if request_time < config["request_time_threshold"]:
            return

    alert_obj = AlertRuleStatus(
        g_cache_engine,
        status,
        config["alert_threshold"],
        config["alert_time_range"],
        config["alert_method_list"]
    )
    alert_obj.run()


def alert_response_time_range(record, config):
    if len(config) == 0:
        return

    upstream_response_time = etl_field("upstream_response_time", record)
    request_length = etl_field("request_length", record)

    if not config["request_length_range"][0] <= request_length <= config["request_length_range"][1]:
        return

    if upstream_response_time <= config["warning_line"]:
        return

    alert_obj = AlertRuleResponseRange(
        g_cache_engine,
        upstream_response_time,
        config["alert_threshold"],
        config["alert_time_range"],
        config["alert_method_list"]
    )
    alert_obj.run()


def alert_response_time_ratio(record, config):
    if len(config) == 0:
        return

    upstream_response_time = etl_field("upstream_response_time", record)
    upstream_response_length = etl_field("upstream_response_length", record)

    if record["request_method"] != "GET" or \
            upstream_response_time < config["response_time_threshold"]:
        return

    if upstream_response_time == 0.0:
        return

    ratio = int(upstream_response_length / upstream_response_time)
    if float(ratio) >= config["warning_line"]:
        return


    alert_obj = AlertRuleResponseRatio(
        g_cache_engine,
        ratio,
        config["alert_threshold"],
        config["alert_time_range"],
        config["alert_method_list"]
    )
    alert_obj.run()

def alert_request_time_ratio(record, config):
    if len(config) == 0:
        return

    request_time = etl_field("request_time", record)
    body_bytes_sent = etl_field("body_bytes_sent", record)

    if record["request_method"] != "GET" or \
            request_time < config["request_time_threshold"] or \
            body_bytes_sent > config["body_sent_byte_warning_line"]:
        return

    if request_time == 0.0:
        return

    ratio = int(body_bytes_sent / request_time)
    if float(ratio) >= config["ratio_warning_line"]:
        return

    alert_obj = AlertRuleRequestRatio(
        g_cache_engine,
        ratio,
        config["alert_threshold"],
        config["alert_time_range"],
        config["alert_method_list"]
    )
    alert_obj.run()


class AlertRuleBase(object):
    def __init__(self, cache_engine, field_value, alert_threshold, alert_time_range, alert_method_list):
        self.cache_engine = cache_engine
        self.alert_threshold = alert_threshold
        self.alert_time_range = alert_time_range
        self.field_value = field_value

        self.message = None
        #self.ALERT_FORMAT = "[Access Log Analysis] Machine: %s, Metric: %s, Reason: %s"
        #simplify message
        self.ALERT_FORMAT = "%s, Reason: %s"
        self.alert_method_list = alert_method_list

        self.alert_keys = None
        self.alert_title = None

    def alert(self):
        self.message = '[Access Log Alarm] Machine: %s, %s' % (g_host_ip, self.message,)
        logging.getLogger("alert").info(self.message)
        for al in self.alert_method_list:
            ALERT_METHOD_HANDLERS[al](self.alert_keys, self.message)

    def make_alert_message(self, current):
        self.message = self.ALERT_FORMAT % (
            #socket.gethostname(),
            self.alert_title,
            "total %s, exceed %s times in %s second" % (current, self.alert_threshold, self.alert_time_range)
        )

    def run(self):
        current = self.cache_engine.incr(self.alert_keys, 1)
        if current is None:
            self.cache_engine.setex(self.alert_keys, 1, self.alert_time_range)
            current = 1

        if current > self.alert_threshold:
            # for alert ratio control
            alert_key = "alert_control_%s" % self.alert_keys
            if alert_key in g_cache_engine:
                return
            g_cache_engine.setex(alert_key, "cooldown", sfg.ALERT_COOLDOWN_SECONDS)

            self.make_alert_message(current)
            self.alert()


class AlertRuleStatus(AlertRuleBase):
    def __init__(self, cache_engine, field_value, alert_threshold, alert_time_range, alert_method_list):
        super(AlertRuleStatus, self).__init__(cache_engine, field_value, alert_threshold, alert_time_range, alert_method_list)

        self.alert_title = "STATUS %s" % self.field_value
        self.alert_keys = "alert_status_%s" % self.field_value


class AlertRuleResponseRange(AlertRuleBase):
    def __init__(self, cache_engine, field_value, alert_threshold, alert_time_range, alert_method_list):
        super(AlertRuleResponseRange, self).__init__(cache_engine, field_value, alert_threshold, alert_time_range, alert_method_list)

        self.alert_title = "RESPONSE RANGE: %s" % self.field_value
        self.alert_keys = "alert_upstream_response_time_range"


class AlertRuleResponseRatio(AlertRuleBase):
    def __init__(self, cache_engine, field_value, alert_threshold, alert_time_range, alert_method_list):
        super(AlertRuleResponseRatio, self).__init__(cache_engine, field_value, alert_threshold, alert_time_range, alert_method_list)

        self.alert_title = "RES RATIO: %s" % self.field_value
        self.alert_keys = "alert_upstream_response_time_ratio"


class AlertRuleRequestRatio(AlertRuleBase):
    def __init__(self, cache_engine, field_value, alert_threshold, alert_time_range, alert_method_list):
        super(AlertRuleRequestRatio, self).__init__(cache_engine, field_value, alert_threshold, alert_time_range, alert_method_list)

        self.alert_title = "REQ RATIO: %s" % self.field_value
        self.alert_keys = "alert_request_time_ratio"

