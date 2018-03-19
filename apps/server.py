#!/usr/bin/env python3
# http://aiosmtpd.readthedocs.io/en/latest/aiosmtpd/docs/smtp.html

import sys
import asyncio
import time
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Proxy

sys.path.append("../modules/")
import sendmq
import returnmq

class Handler(Proxy):
    def __init__(self, remote_hostname, remote_port):
        super(self.__class__, self).__init__(remote_hostname, remote_port)

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
        if not address.endswith("@{localhost}"):
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

        # TODO: Save to temporary directory

        # TODO: message queue handler here
        sender = sendmq.sender(exchange_id="mail",
            routing_keys=["mail.{0}".format(rcpt) for rcpt in envelope.rcpt_tos],
            silent_mode=True)

        # TODO: corr_id mapping
        sender.sendMsg(envelope.content.decode("utf-8", errors="replace"))

        # TODO: Waiting for return
        handler = returnmq.result_handler()
        while True:
            result = handler.get(sender.corr_id)
            if result:
                print(result)
                break
            else:
                print("sleeping ...")
            time.sleep(5)

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
    handler=Handler(remote_hostname="localhost", remote_port=10026),
    hostname="localhost",
    port=8025)

print(" [*] Waiting for emails. To exit press CTRL+C")
SMTPDController.start()

# Do nothing here
# TODO: signal handler
while True:
    time.sleep(5000)

SMTPDController.stop()
