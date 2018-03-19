#!/usr/bin/env python3

from smtplib import SMTP

hostname = "localhost"
port = 8025

client = SMTP(hostname, port)
try:
    r1 = client.sendmail("a@hyili.idv.tw", ["b@hyili.idv.tw"], """\
                    From: Anne Person <anne@hyili.idv.tw>
                    To: Bart Person <bart@hyili.idv.tw>
                    Subject: A test
                    Message-ID: <ant>

                    Hi Bart, this is Anne.
                    """)
except Exception as e:
    print(e)

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

