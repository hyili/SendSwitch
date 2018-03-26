#!/usr/bin/env python3
# http://aiosmtpd.readthedocs.io/en/latest/aiosmtpd/docs/smtp.html
# https://github.com/aio-libs/aiosmtpd

import sys
import json
import asyncio
import time
import random
import copy
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Proxy

sys.path.append("../modules/")
import sendmq
import returnmq

class Handler(Proxy):
    class MQ_Bundle():
        def __init__(self, rcpt, sender):
            # MQ side
            self.rcpt = rcpt
            self.sender = sender

    class SMTP_Bundle():
        def __init__(self, corr_id, rcpt, server, session, envelope):
            # SMTP side
            self.corr_id = corr_id
            self.rcpt = rcpt
            self.server = server
            self.session = session
            self.envelope = copy.deepcopy(envelope)
            self.envelope.rcpt_tos = [rcpt]

    def __init__(self, remote_hostname, remote_port, silent_mode=False):
        super(self.__class__, self).__init__(remote_hostname, remote_port)

        self.remote_hostname = remote_hostname
        self.remote_port = remote_port
        self.silent_mode = silent_mode
        self.handler = returnmq.result_handler()

        self.statistic = 0

        # TODO:
        self.registered_user = []
        self.MQ_Bundles = {}
        self.SMTP_Bundles = {}

    def Debug(self, msg):
        if not self.silent_mode:
            print(" [*] {0}".format(msg))

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
        self.Debug("Message from {0}".format(envelope.mail_from))
        self.Debug("Message from {0}".format(envelope.rcpt_tos))
        self.Debug("Message data:\n")
        self.Debug(envelope.content.decode("utf8", errors="replace"))
        self.Debug("End of message")

        # TODO: Save to temporary directory

        # TODO: Send email & put emails under monitoring
        for rcpt in envelope.rcpt_tos:
            if rcpt in self.registered_user:
                if rcpt not in self.MQ_Bundles:
                    sender = sendmq.sender(exchange_id="mail",
                        routing_keys=["mail.{0}".format(rcpt)],
                        silent_mode=True)
                    self.MQ_Bundles[rcpt] = self.MQ_Bundle(rcpt, sender)
                sender = self.MQ_Bundles[rcpt].sender
                corr_id = sender.sendMsg(envelope.content.decode("utf-8", errors="replace"))
            else:
                if "others" not in self.MQ_Bundles:
                    sender = sendmq.sender(exchange_id="",
                        routing_keys=["return"],
                        silent_mode=True)
                    self.MQ_Bundles["others"] = self.MQ_Bundle(rcpt, sender)
                sender = self.MQ_Bundles["others"].sender
                corr_id = sender.sendMsg("OK")

            bundle = self.SMTP_Bundle(corr_id, rcpt, server, session, envelope)
            self.SMTP_Bundles[corr_id] = bundle

        return "250 OK"

    # STARTTLS Command
    # handle_STARTTLS(server, session, envelope)

    # EXCEPTION
    # handle_exception(error)

    async def handle_returnmq(self):
        while True:
            if len(self.SMTP_Bundles) > 0:
                # Fetching result
                SMTP_Bundles_list = list(self.SMTP_Bundles.keys())
                for corr_id in SMTP_Bundles_list:
                    _result = self.handler.get(corr_id)
                    if _result:
                        result = json.loads(_result)
                        self.Debug(result)
                    else:
                        continue

                    # TODO: Handle the return results
                    if result["result"] == "OK":
                        SMTP_result = await super(self.__class__, self).handle_DATA(
                            self.SMTP_Bundles[corr_id].server,
                            self.SMTP_Bundles[corr_id].session,
                            self.SMTP_Bundles[corr_id].envelope
                        )
                        self.Debug(SMTP_result)
                    elif result["result"] == "pending":
                        SMTP_result = await super(self.__class__, self).handle_DATA(
                            self.SMTP_Bundles[corr_id].server,
                            self.SMTP_Bundles[corr_id].session,
                            self.SMTP_Bundles[corr_id].envelope
                        )
                        self.Debug(SMTP_result)
                    else:
                        # Do nothing
                        pass

                    # Pop finished job from SMTP_Bundles
                    self.Debug("Pop {0}".format(corr_id))
                    self.SMTP_Bundles.pop(corr_id, None)
                    self.statistic += 1
                    self.Debug("Pop {0} Done".format(corr_id))
            else:
                self.Debug("Sleeping")
                await asyncio.sleep(random.random()*10)

    async def some_statistic(self):
        while True:
            start = self.statistic
            await asyncio.sleep(1)
            end = self.statistic
#            print("{0} msg/sec".format(end-start))


# http://aiosmtpd.readthedocs.io/en/latest/aiosmtpd/docs/controller.html?highlight=8025#controller-api
# Asynchronous smtpd server, await many functions to handle the request at the
# same time

# SMTP method handler
handler = Handler(remote_hostname="localhost", remote_port=10026, silent_mode=True)

# Return message handler (From MessageQueue)
loop = asyncio.new_event_loop()
loop.create_task(handler.handle_returnmq())
loop.create_task(handler.some_statistic())

# SMTP server setup
SMTPDController = Controller(
    handler=handler,
    loop=loop,
    hostname="localhost",
    port=8025)

try:
    print(" [*] Waiting for emails. To exit press CTRL+C")
    SMTPDController.start()

    # Do nothing here
    while True:
        time.sleep(random.random())

    SMTPDController.stop()
except KeyboardInterrupt:
    print(" [*] Signal Catched. Quit.")
    SMTPDController.stop()
except Exception as e:
    print(e)
    SMTPDController.stop()
