#!/usr/bin/env python3

from smtplib import SMTP
import time
import sys

hostname = "localhost"
port = 8025

client = SMTP(hostname, port)
print("Start to insert emails.")

try:
    if len(sys.argv) == 2:
        number = int(sys.argv[1])
    else:
        print("please input an integer")
        exit()
except:
    print("args must be an integer")
    exit()

for i in range(0, number, 1):
    try:
        r1 = client.sendmail("a@hyili.idv.tw", ["hyili@hyili.idv.tw"],
"""From: Anne Person <anne@hyili.idv.tw>
To: Bart Person <bart@hyili.idv.tw>
Subject: A test
Message-ID: <ant>

Hi Bart, this is Anne.
""")
    except Exception as e:
        print(e)

    print("... {0} ...".format(i))
