import sys
import os
from supervisor import childutils

from leazy_ext.service.sms2 import SendSMS
from filepicker_monitor import setting as sfg


def write_stdout(s):
    sys.stdout.write(s)
    sys.stdout.flush()

def write_stderr(s):
    sys.stderr.write(s)
    sys.stderr.flush()

def main():
    if not 'SUPERVISOR_SERVER_URL' in os.environ:
        write_stderr("fpmonitor listener can only be started by supervisord.\n")
        sys.exit(1)

    while True:
        headers, payload = childutils.listener.wait(sys.stdin, sys.stdout)

        # only subscribe event PROCESS STATE_FATAL
        if not headers['eventname'] == 'PROCESS_STATE_FATAL':
            childutils.listener.ok(sys.stdout)
            continue

        pheaders, pdata = childutils.eventdata(payload+'\n')
        for mobile in sfg.MONITOR_ALERT_MOBILE:
            SendSMS(
                "filepicker",
                "[filepicker监控]".decode("utf8"),
                mobile,
                "[fpmonitor listener]fpmonitor crash.fromstate %s" % pheaders['from_state'].decode("utf8"),
            )

        childutils.listener.ok(sys.stdout)


if __name__ == '__main__':
    main()
