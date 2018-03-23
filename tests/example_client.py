#!/usr/bin/env python3

from smtplib import SMTP
import time

hostname = "localhost"
port = 25

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

try:
    r2 = client.sendmail("a@hyili.idv.tw", ["c@night.hyili.idv.tw"], """\
                    From: Anne Person <anne@hyili.idv.tw>
                    To: Chris Person <chris@night.hyili.idv.tw>
                    Subject: Another test
                    Message-ID: <another>

                    Hi Chris, this is Anne.
                    """)
except Exception as e:
    print(e)

