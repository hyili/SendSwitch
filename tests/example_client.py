#!/usr/bin/env python3

from smtplib import SMTP
import time
import sys

hostname = "localhost"
port = 8025

client = SMTP(hostname, port)
try:
    if len(sys.argv) >= 4:
        number = int(sys.argv[1])
        mailer = sys.argv[2]
        emails = sys.argv[3:]
    else:
        raise Exception("Show usage")
except:
    print("Usage: ./example_client.py [number_of_email] [mailer] [email_1] [email_2] ...\n")
    print("Ex:    ./example_client.py 3 test@example1.com test@example2.com test@example3.com")
    print("       This will send 3 test emails from test@example1.com to test@example2.com and test@example3.com.")
    exit()

print("Start to insert emails.")
for i in range(0, number, 1):
    try:
        r1 = client.sendmail(mailer_domain, emails,
"""From: Anne Person <test@example1.com>
To: Bart Person <test@example2.com>
Subject: A test
Message-ID: whoowhoohaha

Hi Bart, this is Anne.
""")
    except Exception as e:
        print(e)

    print("... {0} ...".format(i))
