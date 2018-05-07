#!/usr/bin/env python3

from smtplib import SMTP
import time

hostname = "localhost"
port = 8025

client = SMTP(hostname, port)
while True:
    try:
        r1 = client.sendmail("a@hyili.idv.tw", ["hyili@hyili.idv.tw"], """\
                    From: Anne Person <anne@hyili.idv.tw>
                    To: Bart Person <bart@hyili.idv.tw>
                    Subject: A test
                    Message-ID: <ant>

                    Hi Bart, this is Anne.
                    """)
    except Exception as e:
        print(e)

    print("...")
