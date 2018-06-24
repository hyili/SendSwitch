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
import email
import concurrent.futures

from email.header import decode_header
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
        try:
            self.data = self.email_translator(self.envelope.original_content)
        except Exception as e:
            print(" [*] Decode error occurred. {0}".format(e))

            exc_type, exc_value, exc_traceback = sys.exc_info()
            print(traceback.print_exc())

        self.status = 0

    def extract_header(self, p):
        ret = dict()
        for key in set(p.keys()):
            # get all the headers which named key
            value = p.get_all(key, None)
            # init header part
            ret[key.lower()] = list()
            for element in value:
                pair = decode_header(element)
                content = ""
                for (_content, _charset) in pair:
                    if _charset:
                        content = "{0} {1}".format(content, _content.decode(_charset))
                    else:
                        if isinstance(_content, (bytes, bytearray)):
                            content = "{0} {1}".format(content, _content.decode())
                        else:
                            content = "{0} {1}".format(content, _content)
                ret[key.lower()].insert(0, content)

        return ret

    def extract_payload(self, p):
        ret = ""

        for part in p.walk():
            if part.get_content_maintype() == "text":
                charset = part.get_content_charset()
                if charset is not None:
                    payload = part.get_payload(decode=True).decode(charset, errors="replace")
                    ret += payload
                else:
                    payload = part.get_payload(decode=True).decode(errors="replace")
                    ret += payload
            # TODO: Can extend more content type here

        return ret

    def email_translator(self, msg):
        ret = dict()
        p = email.message_from_bytes(msg)

        # Extracting header
        ret["header"] = self.extract_header(p)

        # Extracting payload
        ret["payload"] = self.extract_payload(p)

        # Appending result
        ret["result"] = "Pending"

        # returning
        return ret

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
            self.output.send(" [{0:20s}] {1:36s}, {2:26s}, {3}".
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

        # TODO: only bytes has splitlines
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
                    refused[rcpt] = (reply[0], str(reply[1].decode("utf-8", errors="replace")))
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
        # TODO: relay access control
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
    def __init__(self, config, local, remote, host="localhost", backup_enable=False, temp_directory="/tmp/PSF", silent_mode=False):
        super().__init__(config, local, remote, silent_mode=silent_mode)

        # MQ connections
        self.MQ_Bundles = {}

        # MQ host & port
        self.MQ_host = config.kwargs["MQ_host"]
        self.MQ_port = config.kwargs["MQ_port"]

        # workers
        self.max_workers = config.kwargs["max_workers"]

        # flush queue
        self.flush = config.kwargs["flush"]

        # Backup & Recovery
        self.temp_directory = temp_directory

        # check if temp mail directory exists
        self.backup_enable = backup_enable
        if backup_enable:
            if not os.path.isdir(self.temp_directory):
                os.mkdir(self.temp_directory, 0o755)
            else:
                self.recovery()
                pass

    def finish(self, corr_id):
        bundle = self.SMTP_Bundles.pop(corr_id, None)
        self.local.statistic += 1

        if self.backup_enable:
            try:
                self.Debug("Remove from backup", header=corr_id)
                os.remove("{0}/{1}".format(self.temp_directory, bundle.corr_id))
            except Exception as e:
                self.Debug("Remove failed. Reason: {0}".format(e), header=corr_id)

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
            data["envelope_content"] = bundle.envelope.content
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
                    envelope.content = data["envelope_content"]

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
                host=self.MQ_host,
                port=self.MQ_port,
                silent_mode=True)
            self.MQ_Bundles[rcpt] = MQ_Bundle(rcpt, sender)
        sender = self.MQ_Bundles[rcpt].sender

        # Send out message to MQ with corr_id
        # TODO: Maybe run_in_executor?
        sender.sendMsg(bundle.data, corr_id=bundle.corr_id, result=bundle.data["result"])

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
                if self.backup_enable:
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

    # TODO: more action
    def apply_action(self, bundle, result, user_profile):
        # This handles the message that server send to itself
        if result["result"] == "Pending":
            bundle.status = 0
            SMTP_result = self.send_email(bundle, user_profile)
        # This handles the message that client said let it pass
        elif result["result"] == "OK":
            bundle.status = 1
            SMTP_result = self.send_email(bundle, user_profile)
        elif result["result"] == "Reject":
            bundle.status = -1
            SMTP_result = (451, "Rejected by receiver's content filter, reason: {0}".
                format(result["result"]))
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

            # run every 10*random secs
            await asyncio.sleep(random.random()*10)

    async def timeout_mod(self):
        while True:
            # run every 10*random secs
            await asyncio.sleep(random.random()*10)
            timestamp = int(time.time())

            # check if the mail have flush request
            while True:
                corr_id = self.flush.recv()
                if corr_id is not None:
                    bundle = self.SMTP_Bundles[corr_id]
                    last_retry_timestamp = bundle.last_retry_timestamp
                    rcpt = bundle.rcpt
                    user_profile = self.registered_users.get(rcpt)

                    self.send(bundle, user_profile=user_profile, direct=False)
                    bundle.last_retry_timestamp = timestamp
                else:
                    break

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

                # check if time is up
                if timestamp - last_retry_timestamp > timeout:
                    self.send(bundle, user_profile=user_profile, direct=True)
                    bundle.last_retry_timestamp = timestamp
