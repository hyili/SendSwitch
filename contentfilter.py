#!/usr/bin/env python3

import signal
import sys
import os

import sendmq

# definition
INSPECT_DIR = "/tmp/"
TEMP_FILE = "temp.in"
SENDMAIL = "/usr/sbin/sendmail -G -i"

# reading args
sendmail_args = sys.argv[1:]
sender = sys.argv[2]
recipient = sys.argv[4]

# change current directory

# exit code
EX_TEMPFAIL = 75
EX_UNAVAILABLE = 69

# signal handler
def finish(code):
    exit(code)

def handler(signum, frame):
    print("Quit")
    finish(EX_TEMPFAIL)

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

# start processing
msg = ""
try:
    with open(INSPECT_DIR+TEMP_FILE, "w") as temp:
        # reading from stdin
        for line in sys.stdin:
            if line is ".":
                break
            msg += line
            temp.write(line)
except Exception as e:
    print(e)
    exit(EX_TEMPFAIL)

# filtering
S = server(exchange_id="hello", routing_keys=["hello"])
S.sendMsg(msg)
R = None
while R is None:
    R = S.getResult()

# write back to mail server
if R:
    try:
        with open(INSPECT_DIR+TEMP_FILE, "r") as temp:
            sendmail_cmd = SENDMAIL
            for arg in sendmail_args:
                sendmail_cmd += (" %s" % arg)

            pipe = os.popen("%s" % (sendmail_cmd), mode="w")
            for line in temp:
                pipe.write(line)

            exit(pipe.close())
    except Exception as e:
        print(e)
        exit(EX_TEMPFAIL)
else:
    exit(EX_UNAVAILABLE)
