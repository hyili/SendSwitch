#!/usr/bin/env python3
# http://aiosmtpd.readthedocs.io/en/latest/aiosmtpd/docs/smtp.html
# https://github.com/aio-libs/aiosmtpd

import os
import sys
import json
import asyncio
import time
import random
import copy
import uuid
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Proxy
from aiosmtpd.smtp import Session
from aiosmtpd.smtp import Envelope

sys.path.append("../modules/")
import sendmq
import returnmq

class Handler(Proxy):
    class MQ_Bundle():
        def __init__(self, rcpt, sender):
            # MQ side every session has a bundle
            self.rcpt = rcpt
            self.sender = sender
            self.timestamp = int(time.time())

    class SMTP_Bundle():
        def __init__(self, corr_id, rcpt, server, session, envelope):
            # SMTP side every email has a bundle
            self.corr_id = corr_id
            self.rcpt = rcpt
            self.timestamp = int(time.time())
            self.server = server
            self.session = session
            self.envelope = copy.deepcopy(envelope)
            self.envelope.rcpt_tos = [rcpt]
            self.status = 0

    def __init__(self, remote_hostname, remote_port, silent_mode=False):
        super(self.__class__, self).__init__(remote_hostname, remote_port)

        self.remote_hostname = remote_hostname
        self.remote_port = remote_port
        self.silent_mode = silent_mode
        self.handler = returnmq.result_handler(silent_mode=True)
        self.directory = "/tmp/PSF"

        self.statistic = 0

        self.registered_user = []
        self.MQ_Bundles = {}
        self.SMTP_Bundles = {}

        if not os.path.isdir(self.directory):
            os.mkdir(self.directory, 0o755)
        else:
            self.recovery()

    def Debug(self, msg):
        if not self.silent_mode:
            print(" [*] {0}".format(msg))

    def finish(self, bundle):
        try:
            os.remove("{0}/{1}".format(self.directory, bundle.corr_id))
        except:
            pass

    # backup whole content of envelope
    def backup(self, bundle):
        with open("{0}/{1}".format(self.directory, bundle.corr_id), "a") as f:
            data = {}
            data["corr_id"] = bundle.corr_id
            data["envelope_mailfrom"] = bundle.envelope.mail_from
            data["envelope_rcptto"] = bundle.envelope.rcpt_tos[0]
            data["envelope_content"] = bundle.envelope.content.decode("utf-8", errors="replace")
            data["session_peer"] = bundle.session.peer

            raw_data = json.dumps(data)
            f.write(raw_data)

    # recover whole content of envelope
    def recovery(self):
        filenames = os.listdir(self.directory)
        for filename in filenames:
            with open("{0}/{1}".format(self.directory, filename), "r") as f:
                try:
                    raw_data = f.read()
                    data = json.loads(raw_data)
                    session = Session(None)
                    envelope = Envelope()

                    session.peer = data["session_peer"]
                    envelope.mail_from = data["envelope_mailfrom"]
                    envelope.rcpt_tos = [data["envelope_rcptto"]]
                    envelope.content = data["envelope_content"].encode("utf-8", errors="replace")

                    bundle = self.SMTP_Bundle(data["corr_id"],
                        data["envelope_rcptto"],
                        None, session, envelope
                    )
                    self.SMTP_Bundles[data["corr_id"]] = bundle

                    self.Debug("Recover: {0} from: {1} to: {2}".format(
                        data["corr_id"],
                        data["envelope_mailfrom"],
                        data["envelope_rcptto"]
                    ))

                    # Resend message
                    self.send(bundle)
                except Exception as e:
                    print(e)

    def send(self, bundle):
        # Check if the recepient is in registered_user list
        if bundle.rcpt in self.registered_user:
            self._send(
                rcpt=bundle.rcpt,
                bundle=bundle,
                exchange_id="mail",
                routing_key="mail.{0}".format(bundle.rcpt),
            )
        else:
            self._send(
                rcpt="others",
                bundle=bundle,
                exchange_id="",
                routing_key="return",
            )


    def _send(self, rcpt, bundle, exchange_id, routing_key):
        # Check if the per user connection to MQ is established
        if rcpt not in self.MQ_Bundles:
            sender = sendmq.sender(exchange_id=exchange_id,
                routing_keys=[routing_key],
                silent_mode=True)
            self.MQ_Bundles[rcpt] = self.MQ_Bundle(rcpt, sender)
        sender = self.MQ_Bundles[rcpt].sender

        # Send out message to MQ with corr_id
        sender.sendMsg(bundle.envelope.content.decode("utf-8", errors="replace"),
            corr_id=bundle.corr_id)

        self.Debug("Send {0}: from: {1} to: {2}".format(
            bundle.corr_id,
            bundle.envelope.mail_from,
            bundle.rcpt
        ))

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
        try:
            # Send email & put emails under monitoring
            for rcpt in envelope.rcpt_tos:
                # Save to temporary directory or database
                # including: each content of SMTP_Bundle
                corr_id = str(uuid.uuid4())

                # Monitor list
                bundle = self.SMTP_Bundle(corr_id, rcpt, server, session, envelope)
                self.SMTP_Bundles[corr_id] = bundle

                # Doing backup here to prepare for error recovery
                self.backup(bundle)

                # Send message to MQ
                self.send(bundle)
        except Exception as e:
            return "471 {0}".format(e)

        return "250 OK"

    # STARTTLS Command
    # handle_STARTTLS(server, session, envelope)

    # EXCEPTION
    # handle_exception(error)

    async def returnmq_mod(self):
        while True:
            if len(self.SMTP_Bundles) > 0:
                # Fetching result
                self.handler.checkResult()
                SMTP_Bundles_list = list(self.SMTP_Bundles.keys())
                for corr_id in SMTP_Bundles_list:
                    _result = self.handler.getResult(corr_id)
                    if _result:
                        result = json.loads(_result)
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
                    bundle = self.SMTP_Bundles.pop(corr_id, None)
                    self.Debug("Receive {0}: from: {1} to: {2}".format(
                        corr_id,
                        bundle.envelope.mail_from,
                        bundle.rcpt
                    ))
                    self.finish(bundle)
                    self.statistic += 1

                # Clear all result that does not match anything
                # TODO: recheck, maybe some problem
                self.handler.clear()

            await asyncio.sleep(random.random())

    async def statistic_mod(self):
        while True:
            start = self.statistic
            await asyncio.sleep(1)
            end = self.statistic
#            print("{0} msg/sec".format(end-start))

    async def timeout_mod(self):
        while True:
            await asyncio.sleep(10)
            timestamp = int(time.time())
            for corr_id in self.SMTP_Bundles:
                if timestamp - self.SMTP_Bundles[corr_id].timestamp > 1200:
                    if "others" not in self.MQ_Bundles:
                        sender = sendmq.sender(
                            exchange_id="",
                            routing_keys=["return"],
                            silent_mode=True
                        )
                        self.MQ_Bundles["others"] = self.MQ_Bundle(
                            self.SMTP_Bundles[corr_id].rcpt,
                            sender
                        )
                    sender = self.MQ_Bundles["others"].sender
                    sender.sendMsg(
                        self.SMTP_Bundles[corr_id].envelope.content.decode("utf-8", errors="replace"),
                        corr_id=corr_id
                    )

# http://aiosmtpd.readthedocs.io/en/latest/aiosmtpd/docs/controller.html?highlight=8025#controller-api
# Asynchronous smtpd server, await many functions to handle the request at the
# same time

# SMTP method handler
handler = Handler(remote_hostname="localhost", remote_port=10026, silent_mode=False)

# Return message handler (From MessageQueue)
loop = asyncio.new_event_loop()
loop.create_task(handler.returnmq_mod())
loop.create_task(handler.statistic_mod())
loop.create_task(handler.timeout_mod())

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
