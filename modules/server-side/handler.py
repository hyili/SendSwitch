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
import datetime
import traceback
import concurrent.futures

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Proxy
from aiosmtpd.smtp import Session
from aiosmtpd.smtp import Envelope

import sendmq
import returnmq

EMPTYBYTES = b""
COMMASPACE = ", "
CRLF = b"\r\n"
NLCRE = re.compile(br"\r\n|\r|\n")

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
        self.created_timestamp = int(time.time())
        self.last_retry_timestamp = self.created_timestamp
        self.server = server
        self.session = session
        self.envelope = copy.deepcopy(envelope)
        self.envelope.rcpt_tos = [rcpt]
        self.status = 0

class ProxyHandler(Proxy):
    def __init__(self, config, local, remote, silent_mode=False):
        super().__init__(remote.hostname, remote.port)

        # local server config & remote server config
        self.local = local
        self.remote = remote

        # global config
        self.config = config
        self.registered_servers = config.kwargs["registered_servers"]
        self.registered_users = config.kwargs["registered_users"]

        self.silent_mode = silent_mode
        self.SMTP_Bundles = {}

        # logging
        self.output = config.kwargs["output"]

    def Debug(self, msg, header="*"):
        if not self.silent_mode:
            timestamp = str(datetime.datetime.now())
            print(" [{0:20s}] {1:36s}, {2:26s}, {3:s}".format(self.local.id, header, timestamp, msg))
            self.output.log.append(" [{0:20s}] {1:36s}, {2:26s}, {3}".
                format(self.local.id, header, timestamp, msg))

    def check_result(self, bundle, SMTP_result):
        # Check if sending operation went wrong
        if bundle.status != -1:
            if SMTP_result[0] == 250:
                self.Debug("Successfully send out. {0}".
                    format(SMTP_result), header=bundle.corr_id)
            elif SMTP_result[0] < 0:
                self.Debug("Something went wrong. {0}".
                    format(SMTP_result), header=bundle.corr_id)
                return

                # TODO: Try to combine retring mechanism into timeout_mod
                # retring need the client's result, timeout don't
                # It is no need to worry about currently
            else:
                self.Debug("Something happened. {0}".
                    format(SMTP_result), header=bundle.corr_id)
                return
        else:
            self.Debug("Remove it. {0}".
                format(SMTP_result), header=bundle.corr_id)

        # Pop finished job from SMTP_Bundles
        self.finish(bundle.corr_id)

        return

    def finish(self, corr_id):
        bundle = self.SMTP_Bundles.pop(corr_id, None)
        self.local.statistic += 1

        user_profile = self.registered_users.get(bundle.rcpt)
        # remove from queuing list
        if user_profile:
            user_profile.remove_queuing(corr_id)

    def send_email(self, bundle, user_profile):
        # get next hostname and port according to user's settings
        remote_server = None
        remote_hostname = None
        remote_port = None

        try:
            remote_server = user_profile.settings[self.local.id]
            remote_hostname = self.registered_servers.get(remote_server).hostname
            remote_port = self.registered_servers.get(remote_server).port
        except Exception as e:
            remote_server = self.remote.id
            remote_hostname = self.remote.hostname
            remote_port = self.remote.port

        self.Debug("Next hop id: {0}, host: {1}, port: {2}".
            format(remote_server, remote_hostname,
            remote_port), header=bundle.corr_id)

        # check if content is not str
        if isinstance(bundle.envelope.content, str):
            content = bundle.envelope.original_content
        else:
            content = bundle.envelope.content
        lines = content.splitlines(keepends=True)

        index = 0
        ending = CRLF
        for line in lines:
            if NLCRE.match(line):
                ending = line
                break
            index += 1

        peer = bundle.session.peer[0].encode("ascii")
        lines.insert(index, b"X-Peer: %s%s" % (peer, ending))
        data = EMPTYBYTES.join(lines)

        try:
            refused = self._send_email(bundle.envelope.mail_from, bundle.envelope.rcpt_tos, data, remote_hostname, remote_port)
        except Exception as e:
            return (471, "Failed. reason: {0}".format(e))

        return refused[bundle.rcpt]

    def _send_email(self, mail_from, rcpt_tos, data, remote_hostname,
        remote_port):

        refused = {}

        # TODO: Need to solve hanging problem here
        try:
            s = smtplib.SMTP(timeout=10)
            s.connect(remote_hostname, remote_port)
            try:
                # Though s.sendmail can done almost everything, it cannot get the reply
                s.docmd("HELO {0}".format(self.config.kwargs["host_domain"]))
                s.docmd("MAIL FROM:<{0}>".format(mail_from))
                for rcpt in rcpt_tos:
                    s.docmd("RCPT TO:<{0}>".format(rcpt))
                s.docmd("DATA")
                s.send(data)
                s.send("\r\n.\r\n")
                reply = s.getreply()
                for rcpt in rcpt_tos:
                    refused[rcpt] = (reply[0], str(reply[1].decode(errors="replace")))
            finally:
                s.quit()
        except smtplib.SMTPRecipientsRefused as e:
            refused = e.recipients
        except smtplib.SMTPException as e:
            # All recipients were refused.  If the exception had an associated
            # error code, use it.  Otherwise, fake it with a non-triggering
            # exception code.
            errcode = getattr(e, "smtp_code", -1)
            errmsg = getattr(e, "smtp_error", str(e))
            for rcpt in rcpt_tos:
                refused[rcpt] = (errcode, errmsg)
        except Exception as e:
            errcode = -2
            errmsg = str(e)
            for rcpt in rcpt_tos:
                refused[rcpt] = (errcode, errmsg)

        return refused

    # RCPT TO Command
    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
#        if not address.endswith("{0}".format(self.config.kwargs["email_domain"])):
#            return "550 not relaying to that domain."
        envelope.rcpt_tos.append(address)
        return "250 OK"

    # DATA Command
    async def handle_DATA(self, server, session, envelope):
        try:
            # Send email & put emails under monitoring
            for rcpt in envelope.rcpt_tos:
                corr_id = str(uuid.uuid4())

                # Monitor list
                bundle = SMTP_Bundle(corr_id, rcpt, server, session, envelope)
                self.SMTP_Bundles[corr_id] = bundle

                # Check if the receiver is registered
                user_profile = self.registered_users.get(rcpt)

                # Send message to next hop
                SMTP_result = self.send_email(bundle, user_profile)

                # Transform to return string
                result = "250 OK, saved as {0}, next hop status: {1}".format(corr_id, str(SMTP_result))

                # Check result
                self.check_result(bundle, SMTP_result)

        except Exception as e:
            return "471 {0}".format(e)

        return result

class MQHandler(ProxyHandler):
    def __init__(self, config, local, remote, silent_mode=False):
        super().__init__(config, local, remote)

        self.MQ_Bundles = {}

        # workers
        self.max_workers = config.kwargs["max_workers"]

        # flush queue
        self.flush_queue = config.kwargs["flush_queue"]

        # Backup & Recovery
        # TODO: location configuration extraction
        self.temp_directory = "/tmp/PSF"

        # check if temp mail directory exists
        if not os.path.isdir(self.temp_directory):
            os.mkdir(self.temp_directory, 0o755)
        else:
            self.recovery()

    def finish(self, corr_id):
        bundle = self.SMTP_Bundles.pop(corr_id, None)
        self.local.statistic += 1

        try:
            self.Debug("Remove from backup", header=corr_id)
            os.remove("{0}/{1}".format(self.temp_directory, bundle.corr_id))
        except Exception as e:
            self.Debug("Remove failed. Reason: {0}".format(e),
                header=corr_id)

        user_profile = self.registered_users.get(bundle.rcpt)
        # remove from queuing list
        if user_profile:
            user_profile.remove_queuing(corr_id)

    # backup whole content of envelope
    def backup(self, bundle, mode="a"):
        with open("{0}/{1}".format(self.temp_directory, bundle.corr_id), mode) as f:
            # TODO: created_timestamp information will lost here
            # Don't know if it will casue any problem
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
        filenames = os.listdir(self.temp_directory)
        for filename in filenames:
            with open("{0}/{1}".format(self.temp_directory, filename), "r") as f:
                try:
                    raw_data = f.read()
                    data = json.loads(raw_data)
                    session = Session(None)
                    envelope = Envelope()

                    session.peer = data["session_peer"]
                    envelope.mail_from = data["envelope_mailfrom"]
                    envelope.rcpt_tos = [data["envelope_rcptto"]]
                    envelope.content = data["envelope_content"].encode("utf-8", errors="replace")

                    bundle = SMTP_Bundle(data["corr_id"],
                        data["envelope_rcptto"],
                        None, session, envelope
                    )
                    self.SMTP_Bundles[data["corr_id"]] = bundle

                    self.Debug("Recover from: {0} to: {1}".format(
                        data["envelope_mailfrom"],
                        data["envelope_rcptto"]
                    ), header=data["corr_id"])

                    # TODO: there is nothing in registered_users when restart
                    # Resend message
                    # Check if the receiver is registered
                    user_profile = self.registered_users.get(bundle.rcpt)
                    if user_profile is not None:
                        # Add corr_id to user's queuing_list
                        user_profile.add_queuing(corr_id)

                    # Send message to MQ
                    self.send(bundle, user_profile=user_profile)
                except Exception as e:
                    print(e)

    def send(self, bundle, user_profile=None, direct=False):
        if not direct:
            # Check if the recepient is in registered_users list
            if user_profile:
                self._send(
                    rcpt=bundle.rcpt,
                    bundle=bundle,
                    user_profile=user_profile,
                    exchange_id="mail",
                    routing_key="mail.{0}".format(bundle.rcpt),
                )
            else:
                self._send(
                    rcpt="others",
                    bundle=bundle,
                    user_profile=user_profile,
                    exchange_id="",
                    routing_key="return",
                )
        else:
            self._send(
                rcpt="others",
                bundle=bundle,
                user_profile=user_profile,
                exchange_id="",
                routing_key="return",
            )

    def _send(self, rcpt, bundle, user_profile, exchange_id, routing_key):
        # Check if the per user connection to MQ is established
        if rcpt not in self.MQ_Bundles:
            sender = sendmq.sender(exchange_id=exchange_id,
                routing_keys=[routing_key],
                user_profile=user_profile,
                silent_mode=True)
            self.MQ_Bundles[rcpt] = MQ_Bundle(rcpt, sender)
        sender = self.MQ_Bundles[rcpt].sender

        # Send out message to MQ with corr_id
        # TODO: Maybe run_in_executor?
        sender.sendMsg(bundle.envelope.content.decode("utf-8", errors="replace"),
            corr_id=bundle.corr_id)

        self.Debug("Send from: {0}, to: {1}".format(
            bundle.envelope.mail_from,
            bundle.rcpt
        ), header=bundle.corr_id)

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
    # handle_RCPT(server, session, envelope, address, rcpt_options)

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
                bundle = SMTP_Bundle(corr_id, rcpt, server, session, envelope)
                self.SMTP_Bundles[corr_id] = bundle

                # Doing backup here to prepare for error recovery
                self.backup(bundle)

                # Check if the receiver is registered
                user_profile = self.registered_users.get(rcpt)
                if user_profile:
                    # Add corr_id to user's queuing_list
                    user_profile.add_queuing(corr_id)

                # Send message to MQ
                self.send(bundle, user_profile=user_profile)

                # Transform to return string
                result = "250 OK, saved as {0}".format(corr_id)

        except Exception as e:
            return "471 {0}".format(e)

        return result

    # STARTTLS Command
    # handle_STARTTLS(server, session, envelope)

    # EXCEPTION
    # handle_exception(error)

    def apply_action(self, bundle, result, user_profile):
        # This handles the message that server send to itself
        if result["result"] == "Pending":
            bundle.status = 0
            SMTP_result = self.send_email(bundle, user_profile)
        # This handles the message that client said let it pass
        elif result["result"] == "OK":
            bundle.status = 1
            SMTP_result = self.send_email(bundle, user_profile)
        # Others drop
        else:
            bundle.status = -1
            SMTP_result = (451, "Rejected by receiver's content filter, reason: {0}".
                format(result["result"]))

        # Check result and update bundle status
        self.check_result(bundle, SMTP_result)

        return

    async def returnmq_mod(self):
        self.handler = returnmq.result_handler(silent_mode=True)
        loop = asyncio.get_event_loop()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)

        while True:
            # Subtask list
            subtasks = list()

            if len(self.SMTP_Bundles) > 0:
                # Fetching result from MQ
                self.handler.checkResult()

                # Get current waiting list
                waiting_list = list(self.handler.getCurrentId())

                # Check if id in waiting list are all legal
                for corr_id in waiting_list:
                    # Fetching the emails
                    if corr_id in self.SMTP_Bundles.keys():
                        _result = self.handler.getResult(corr_id)
                        result = json.loads(_result)
                    else:
                        self.handler.remove(corr_id)
                        continue

                    bundle = self.SMTP_Bundles[corr_id]
                    user_profile = self.registered_users.get(bundle.rcpt)

                    self.Debug("Receive from: {0}, to: {1}".format(
                        bundle.envelope.mail_from, bundle.rcpt),header=corr_id)

                    # Sol.1 Apply the action that client told us
                    #await self.apply_action(bundle, result, user_profile)

                    # Sol.2 Prepare subtask for loop
                    #subtasks.append(self.apply_action(bundle, result, user_profile))

                    # Sol.3
                    # TODO: maybe grouping by each users?
                    # https://docs.python.org/3/library/asyncio-dev.html#handle-blocking-functions-correctly
                    task = loop.run_in_executor(None, self.apply_action, bundle, result, user_profile)
                    subtasks.append(task)

                #Execute the subtask
                # Though it can asynchoronously execute the task
                # But it will still block until all tsaks done
                await asyncio.gather(*subtasks)

            # run every 5 secs
            await asyncio.sleep(5)

    async def timeout_mod(self):
        while True:
            # run every 10 secs
            await asyncio.sleep(10)
            timestamp = int(time.time())

            # run through every monitored emails
            for corr_id in self.SMTP_Bundles:
                bundle = self.SMTP_Bundles[corr_id]
                last_retry_timestamp = bundle.last_retry_timestamp
                rcpt = bundle.rcpt
                user_profile = self.registered_users.get(rcpt)

                # set timeout, *2 means to wait for MQ Message timeout first
                if user_profile is None:
                    timeout = self.config.kwargs["timeout"] * 2
                else:
                    timeout = user_profile.timeout * 2

                # check if the mail have flush request
                if corr_id in self.flush_queue:
                    self.send(bundle, user_profile=user_profile, direct=False)
                    bundle.last_retry_timestamp = timestamp
                # check if time is up
                elif timestamp - last_retry_timestamp > timeout:
                    self.send(bundle, user_profile=user_profile, direct=True)
                    bundle.last_retry_timestamp = timestamp
