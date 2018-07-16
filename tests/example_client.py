#!/usr/bin/env python3

from smtplib import SMTP
import email
import time
import sys

hostname = "localhost"
port = 8025

# if SPAM_ENABLE is True, then a GTUBE pattern will be sent
SPAM_ENABLE = True
VIRUS_ENABLE = False
GTUBE = "XJS*C4JDBQADN1.NSBN3*2IDNEN*GTUBE-STANDARD-ANTI-UBE-TEST-EMAIL*C.34X"
EICAR = "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

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

subject = "A test"
content_template = """{0}"""

if SPAM_ENABLE:
    print("Start to insert spam test emails.")
    content = content_template.format(GTUBE)
elif VIRUS_ENABLE:
    print("Start to insert virus test emails.")
    content = content_template.format(EICAR)
else:
    print("Start to insert emails.")
    content = content_template.format("Hi Bart, this is Anne.")

for i in range(0, number, 1):
    try:
        msg = email.message.EmailMessage()
        msg.set_content(content)
        msg["From"] = mailer
        msg["To"] = emails
        msg["Subject"] = subject

        client.send_message(msg, to_addrs=emails)
    except Exception as e:
        print(e)

    print("... {0} ...".format(i))

client.quit()
