#!/usr/bin/env python3
# http://aiosmtpd.readthedocs.io/en/latest/aiosmtpd/docs/smtp.html
# https://github.com/aio-libs/aiosmtpd

import os
import re
import sys
import json
import asyncio
import time
import random
import copy
import uuid
import smtplib
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Proxy
from aiosmtpd.smtp import Session
from aiosmtpd.smtp import Envelope

import sendmq
import returnmq

EMPTYBYTES = b''
COMMASPACE = ', '
CRLF = b'\r\n'
NLCRE = re.compile(br'\r\n|\r|\n')

class MQHandler(Proxy):
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

    def __init__(self, config, local, remote, silent_mode=False):
        super(self.__class__, self).__init__(remote.hostname, remote.port)

        self.config = config
        self.local = local
        self.remote = remote
        self.silent_mode = silent_mode
        self.directory = "/tmp/PSF"

        self.statistic = 0

        self.registered_servers = config.kwargs["registered_servers"]
        self.registered_users = config.kwargs["registered_users"]
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

    def send(self, bundle, direct=False):
        if not direct:
            # Check if the recepient is in registered_users list
            if self.registered_users.get(bundle.rcpt):
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
                user_profile=self.registered_users.get(rcpt),
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

    async def send_email(self, rcpt, session, envelope):
        # get next hostname and port according to user's settings
        remote_server = None
        remote_hostname = None
        remote_port = None
        user = self.registered_users.get(rcpt)

        try:
            remote_server = user.settings[self.local.id]
            remote_hostname = self.registered_servers.get(remote_server).hostname
            remote_port = self.registered_servers.get(remote_server).port
        except Exception as e:
            remote_server = self.remote.id
            remote_hostname = self.remote.hostname
            remote_port = self.remote.port

        self.Debug("Next hop id:{0} host:{1} port:{2}".format(remote_server,
            remote_hostname, remote_port))

        # check if content is not str
        if isinstance(envelope.content, str):
            content = envelope.original_content
        else:
            content = envelope.content
        lines = content.splitlines(keepends=True)

        index = 0
        ending = CRLF
        for line in lines:
            if NLCRE.match(line):
                ending = line
                break
            index += 1

        peer = session.peer[0].encode('ascii')
        lines.insert(index, b'X-Peer: %s%s' % (peer, ending))
        data = EMPTYBYTES.join(lines)
        refused = self._send_email(envelope.mail_from, envelope.rcpt_tos, data,
            remote_hostname, remote_port)

        # TODO: what to do with refused addresses?

        if len(refused) > 0:
            return str(refused)
        else:
            return {'250 OK'}

    def _send_email(self, mail_from, rcpt_tos, data, remote_hostname,
        remote_port):

        refused = {}

        try:
            s = smtplib.SMTP()
            s.connect(remote_hostname, remote_port)
            try:
                refused = s.sendmail(mail_from, rcpt_tos, data)
            finally:
                s.quit()
        except smtplib.SMTPRecipientsRefused as e:
            refused = e.recipients
        except (OSError, smtplib.SMTPException) as e:
            # All recipients were refused.  If the exception had an associated
            # error code, use it.  Otherwise, fake it with a non-triggering
            # exception code.
            errcode = getattr(e, 'smtp_code', -1)
            errmsg = getattr(e, 'smtp_error', 'ignore')
            for r in rcpt_tos:
                refused[r] = (errcode, errmsg)

        return refused

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
        if not address.endswith("@{0}".format(self.config.kwargs["email_domain"])):
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
        self.handler = returnmq.result_handler(silent_mode=True)
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
                    # TODO: If something happened during send?
                    if result["result"] == "OK":
                        SMTP_result = await self.send_email(
                            self.SMTP_Bundles[corr_id].rcpt,
                            self.SMTP_Bundles[corr_id].session,
                            self.SMTP_Bundles[corr_id].envelope,
                        )
                        self.Debug(SMTP_result)
                    elif result["result"] == "pending":
                        SMTP_result = await self.send_email(
                            self.SMTP_Bundles[corr_id].rcpt,
                            self.SMTP_Bundles[corr_id].session,
                            self.SMTP_Bundles[corr_id].envelope,
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
            #print("{0} msg/sec".format(end-start))

    async def timeout_mod(self):
        while True:
            # run every 10 secs
            await asyncio.sleep(10)
            timestamp = int(time.time())

            # run through every monitored emails
            for corr_id in self.SMTP_Bundles:
                bundle = self.SMTP_Bundles[corr_id]
                create_timestamp = bundle.timestamp
                rcpt = bundle.rcpt
                user_profile = self.registered_users.get(rcpt)

                if timestamp - create_timestamp > user_profile.timeout * 2:
                    self.send(bundle, direct=True)


# TODO: routing
class ProxyHandler(Proxy):
    def __init__(self, config, local, remote, silent_mode=False):
        super(self.__class__, self).__init__(remote.hostname, remote.port)

        self.config = config
        self.local = local
        self.remote = remote
        self.silent_mode = silent_mode

        self.registered_servers = config.kwargs["registered_servers"]
        self.registered_users = config.kwargs["registered_users"]
