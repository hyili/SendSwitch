#!/usr/bin/env python3

import signal
import sys
import os
import time

import sendmq

# definition
INSPECT_DIR = "/tmp/"
TEMP_FILE = "temp.in"
SENDMAIL = "/usr/sbin/sendmail -G -i"
counter = 0
max_retries = 5

# reading args
sendmail_args = sys.argv[1:]
sender = sys.argv[2]
recipient = sys.argv[4]

# signal handler
def finish(code):
    exit(code)

def handler(signum, frame):
    print("Quit")
    finish(os.EX_TEMPFAIL)

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
    exit(os.EX_TEMPFAIL)

# filtering
S = sendmq.server(exchange_id="postfix",
        routing_keys=[recipient],
        silent_mode=True)
S.sendMsg(msg)
R = S.getResult()
while len(R) != 1 and counter < max_retries:
    counter += 1
    time.sleep(5)
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

            pipe.close()
            exit(os.EX_OK)
    except Exception as e:
        print(e)
        exit(os.EX_TEMPFAIL)
else:
    exit(os.EX_TEMPFAIL)
