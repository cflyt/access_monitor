#!/usr/bin/env python
# -*- coding: utf-8 -*-


############# SCRIPT RELATED #################

RUN_TYPE_AUTO = 1
RUN_TYPE_MANUAL = 2

############### LOG RELATED #################

LOG_FORMAT = '$request_time $remote_addr - $remote_user [$time_local] "$request" ' \
             '$status $body_bytes_sent "$http_referer" ' \
             '"$http_user_agent" "$http_x_forwarded_for" $upstream_addr $http_session_id $upstream_machine ' \
             '$request_method "$uri" $upstream_response_length $upstream_response_time $upstream_status ' \
             '$request_length'

LOG_FORMAT =  '$request_time # $remote_addr # $remote_user # [$time_local] # ' \
                      '$request # $status # $body_bytes_sent # ' \
                      '$http_referer # $http_user_agent # ' \
                      '$request_length # $upstream_addr # $request_method # ' \
                      '$uri # $upstream_response_length # $upstream_response_time # $upstream_status';

REGEX_SPECIAL_CHARS = r'([\.\*\+\?\|\(\)\{\}\[\]])'
REGEX_LOG_FORMAT_VARIABLE = r'\$([a-zA-Z0-9\_]+)'


LOG_FIELDS = [
    "status",
    "body_bytes_sent",
    "request_time",
    "upstream_response_time",
    "upstream_response_length",
    "request_length",
    "bytes_sent"
]


################# LOGGING ########################
LOGGING = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(name)-12s %(asctime)s %(levelname)-8s %(message)s'
        }
    },
    'handlers': {
        #输出到控制台
        'console':{
            'level':'DEBUG',    #输出信息的最低级别
            'class':'logging.StreamHandler',
        },
        'monitor': {
            'level': 'DEBUG',
            'formatter': 'default',
            'class': 'logging.FileHandler',
            'filename': 'var/log/monitor.log'
        },
        'alert': {
            'level': 'INFO',
            'formatter': 'default',
            'class': 'logging.FileHandler',
            'filename': 'var/log/alert.log'
        },
    },

    'root': {
            'handlers': ['monitor','console'],
            'level': 'DEBUG',
     },
    'loggers': {

        'alert': {
            'handlers': ['alert',],
            'level': 'INFO',
        }
   }
}

ALERT_COOLDOWN_SECONDS = 20

ALERT_MOBILES = [
]
ALERT_EMAILS = [
]

