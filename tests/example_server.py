#!/usr/bin/env python3
# http://aiosmtpd.readthedocs.io/en/latest/aiosmtpd/docs/smtp.html

import asyncio
import time
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Proxy

class TestHandler(Proxy):
    # http://aiosmtpd.readthedocs.io/en/latest/aiosmtpd/docs/handlers.html#handler-hooks
    # HELO Command
    # handle_HELO(server, session, envelope, hostname)

    # EHLO Command
    # handle_EHLO(server, session, envelope, hostname)

    # NOOP Command
    # handle_NOOP(server, session, envelope, arg)

    # QUIT Command
    # handle_QUIT(server, session, envelope)

    # VEFY Command
    # handle_VRFY(server, session, envelope, address)

    # MAIL FROM Command
    # handle_MAIL(server, session, envelope, address, mail_options)

    # RCPT TO Command
    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        if not address.endswith("@hyili.idv.tw"):
            return "550 not relaying to that domain."
        envelope.rcpt_tos.append(address)
        return "250 OK"

    # RSET Command
    # handle_RSET(server, session, envelope)

    # DATA Command
    async def handle_DATA(self, server, session, envelope):
        # Print out messages first
        print("Message from {0}".format(envelope.mail_from))
        print("Message from {0}".format(envelope.rcpt_tos))
        print("Message data:\n")
        print(envelope.content.decode("utf8", errors="replace"))
        print("End of message")

        # Then, wait for Proxy to send messages back
        result =  await super(self.__class__, self).handle_DATA(server,
            session,
            envelope)

        # Output the result
        #return "250 Message accepted for delivery"
        return result

    # STARTTLS Command
    # handle_STARTTLS(server, session, envelope)

    # EXCEPTION
    # handle_exception(error)

# http://aiosmtpd.readthedocs.io/en/latest/aiosmtpd/docs/controller.html?highlight=8025#controller-api
# Asynchronous smtpd server, await many functions to handle the request at the
# same time
SMTPDController = Controller(
    handler=TestHandler(remote_hostname="localhost", remote_port=10026),
    hostname="localhost",
    port=8025)

SMTPDController.start()

# Do nothing here
# TODO: signal handler
while True:
    time.sleep(5000)

SMTPDController.stop()
