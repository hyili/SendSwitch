#!/usr/bin/env python3

from smtplib import SMTP
import time
import sys

hostname = "localhost"
port = 8025

client = SMTP(hostname, port)
print("Start to insert emails.")

try:
    if len(sys.argv) >= 3:
        number = int(sys.argv[1])
        emails = sys.argv[2:]
    else:
        raise Exception("Show usage")
except:
    print("Usage: ./example_client.py [number_of_email] [email_1] [email_2] ...")
    exit()

for i in range(0, number, 1):
    try:
        r1 = client.sendmail("test@example1.com", emails,
"""From: Anne Person <test@example1.com>
To: Bart Person <test@example2.com>
Subject: A test
Message-ID: whoowhoohaha

Hi Bart, this is Anne.
""")
    except Exception as e:
        print(e)

    print("... {0} ...".format(i))
