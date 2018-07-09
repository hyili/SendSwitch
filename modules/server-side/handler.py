#!/usr/bin/env python3
# http://aiosmtpd.readthedocs.io/en/latest/aiosmtpd/docs/smtp.html
# https://github.com/aio-libs/aiosmtpd

import os
import re
import sys
import json
import base64
import asyncio
import time
import random
import copy
import uuid
import smtplib
import datetime
import traceback
import concurrent.futures

from aiosmtpd.handlers import Proxy
from aiosmtpd.smtp import Session
from aiosmtpd.smtp import Envelope

from mq import sendmq
from mq import returnmq
import macro

EMPTYBYTES = b""
COMMASPACE = ", "
CRLF = b"\r\n"
NLCRE = re.compile(br"\r\n|\r|\n")

class MQHandlerBundle():
    def __init__(self, rcpt, sender):
        # MQ side every session has a bundle
        self.rcpt = rcpt
        self.sender = sender
        self.timestamp = int(time.time())

class SMTPSessionBundle():
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

    def email_translator(self, msg):
        ret = base64.b64encode(msg).decode()

        return ret

class SMTPProxyHandler(Proxy):
    def __init__(self, config, current_server, next_hop_server, silent_mode=False):
        super().__init__(next_hop_server.hostname, next_hop_server.port)

        # current_server server config & next_hop_server server config
        self.current_server = current_server
        self.next_hop_server = next_hop_server

        # global config
        self.config = config
        self.registered_servers = config.kwargs["registered_servers"]
        self.registered_users = config.kwargs["registered_users"]
        self.registered_user_routes = config.kwargs["registered_user_routes"]

        self.silent_mode = silent_mode
        self.SMTP_session_bundles = {}

        # logging
        self.output = config.kwargs["output"]

    def Debug(self, msg, header="*"):
        if not self.silent_mode:
            timestamp = str(datetime.datetime.now())
            print(" [{0:20s}] {1:36s}, {2:26s}, {3:s}".format(self.current_server.sid, header, timestamp, msg))
            self.output.send(" [{0:20s}] {1:36s}, {2:26s}, {3}".
                format(self.current_server.sid, header, timestamp, msg))

    def check_SMTP_result(self, bundle, SMTP_result):
        # Check if sending operation went wrong
        if bundle.status != -1:
            if SMTP_result[0] == 250:
                self.Debug("Successfully send out. {0}".
                    format(SMTP_result), header=bundle.corr_id)
            elif SMTP_result[0] < 0:
                self.Debug("Something went wrong. {0}".
                    format(SMTP_result), header=bundle.corr_id)

                return "471 Something wrong happened to {0}, next hop status {1}".format(bundle.corr_id, str(SMTP_result))
            else:
                self.Debug("Something happened. {0}".
                    format(SMTP_result), header=bundle.corr_id)

                return "471 Something wrong happened to {0}, next hop status {1}".format(bundle.corr_id, str(SMTP_result))
        else:
            self.Debug("Remove it. {0}".
                format(SMTP_result), header=bundle.corr_id)

        # Pop finished job from SMTP_session_bundles
        self.finish(bundle.corr_id)

        return "250 OK saved as {0}, next hop status {1}".format(bundle.corr_id, str(SMTP_result))

    def finish(self, corr_id):
        bundle = self.SMTP_session_bundles.pop(corr_id, None)

        user_profile = self.registered_users.get(bundle.rcpt)

        # TODO: remove from queuing list

    def send_email(self, bundle, user_profile):
        # TODO: loop prevention
        # get next hostname and port according to user's settings
        next_hop_server_sid = self.next_hop_server.sid
        next_hop_server_hostname = self.next_hop_server.hostname
        next_hop_server_port = self.next_hop_server.port

        if user_profile.route_ready:
            #user_next_hop_server = self.next_hop_server
            #next_hop_server_sid = user_next_hop_server.sid
            #next_hop_server_hostname = user_next_hop_server.hostname
            #next_hop_server_port = user_next_hop_server.port
            user_route = self.registered_user_routes.get(user_profile.id, self.current_server.id)
            if user_route:
                next_hop_server_sid = user_route.dest.sid
                next_hop_server_hostname = user_route.dest.hostname
                next_hop_server_port = user_route.dest.port

        self.Debug("Next hop id: {0}, host: {1}, port: {2}".
            format(next_hop_server_sid, next_hop_server_hostname,
            next_hop_server_port), header=bundle.corr_id)

        content = bundle.envelope.original_content
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
            refused = self._send_email(bundle.envelope.mail_from, bundle.envelope.rcpt_tos, data, next_hop_server_hostname, next_hop_server_port)
        except Exception as e:
            return (471, "Failed. reason: {0}".format(e))

        # TODO: this will have problem when group mailing is implemented
        return refused[bundle.rcpt]

    def _send_email(self, mail_from, rcpt_tos, data, next_hop_server_hostname, next_hop_server_port):
        refused = {}

        try:
            s = smtplib.SMTP()
            s.connect(next_hop_server_hostname, next_hop_server_port)
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
        envelope.rcpt_tos.append(address)
        return "250 OK"

    # DATA Command
    async def handle_DATA(self, server, session, envelope):
        try:
            # Send email & put emails under monitoring
            for rcpt in envelope.rcpt_tos:
                corr_id = str(uuid.uuid4())

                # Monitor list
                bundle = SMTPSessionBundle(corr_id, rcpt, server, session, envelope)
                self.SMTP_session_bundles[corr_id] = bundle

                # Check if the receiver is registered
                user_profile = self.registered_users.get(rcpt)

                # Send message to next hop, run_in_executor to prevent blocking
                loop = asyncio.get_event_loop()
                task = loop.run_in_executor(None, self.send_email, bundle, user_profile)
                finished, pending = await asyncio.wait([task])
                for r in finished:
                    SMTP_result = r.result()

                # Check result
                result = self.check_SMTP_result(bundle, SMTP_result)

        except Exception as e:
            return "471 Something wrong happened, {0}".format(e)

        return result

class SMTPMQHandler(SMTPProxyHandler):
    def __init__(self, config, current_server, next_hop_server, host="localhost", backup_enable=False, temp_directory="/tmp/PSF/", silent_mode=False):
        super().__init__(config, current_server, next_hop_server, silent_mode=silent_mode)

        # MQ connections
        self.MQ_handler_bundles = {}

        # MQ host & port
        self.MQ_host = config.kwargs["MQ_host"]
        self.MQ_port = config.kwargs["MQ_port"]

        # Subtask list
        self.subtasks = list()

        # workers
        self.max_workers = config.kwargs["max_workers"]

        # flush queue
        self.flush = config.kwargs["flush"]

        # retry interval
        self.retry_interval = config.kwargs["retry_interval"]

        # Backup & Recovery
        self.temp_directory = temp_directory
        self.temp_envelope_directory = "{0}envelope/".format(temp_directory)
        self.temp_origin_directory = "{0}origin/".format(temp_directory)

        # check if temp mail directory exists
        self.backup_enable = backup_enable
        if backup_enable:
            self.init()
            self.recovery()

    def __del__(self):
        for subtask in self.subtasks:
            subtask.cancel()

    def init(self):
        try:
            # set directory permission
            if not os.path.isdir(self.temp_directory):
                os.mkdir(self.temp_directory, 0o700)
            if not os.path.isdir(self.temp_envelope_directory):
                os.mkdir(self.temp_envelope_directory, 0o700)
            if not os.path.isdir(self.temp_origin_directory):
                os.mkdir(self.temp_origin_directory, 0o700)
        except Exception as e:
            self.Debug("Something went wrong during initialization of backup directory. {0}".format(e))
            self.Debug("Disable backup mode.")
            self.backup_enable = False

    def finish(self, corr_id):
        bundle = self.SMTP_session_bundles.pop(corr_id, None)

        if self.backup_enable:
            try:
                self.Debug("Remove from backup", header=corr_id)
                os.remove("{0}{1}".format(self.temp_envelope_directory, bundle.corr_id))
                os.remove("{0}{1}".format(self.temp_origin_directory, bundle.corr_id))
            except Exception as e:
                self.Debug("Remove failed. Reason: {0}".format(e), header=corr_id)

        user_profile = self.registered_users.get(bundle.rcpt)

        # TODO: remove from queuing list

    # backup whole content of envelope
    def backup(self, bundle):
        try:
            with open("{0}{1}".format(self.temp_envelope_directory, bundle.corr_id), "w") as fe:
                # TODO: created_timestamp information will lost here
                # Don't know if it will casue any problem
                data = {}
                data["corr_id"] = bundle.corr_id
                data["envelope_mailfrom"] = bundle.envelope.mail_from
                data["envelope_rcptto"] = bundle.envelope.rcpt_tos[0]
                data["session_peer"] = bundle.session.peer

                raw_data = json.dumps(data)
                fe.write(raw_data)
                with open("{0}{1}".format(self.temp_origin_directory, bundle.corr_id), "wb") as fo:
                    # write original email content
                    fo.write(bundle.envelope.original_content)
        except Exception as e:
            self.Debug("Something went wrong during backup. {0}".format(e))
            self.Debug("Reinitialize.")
            try:
                self.init()
                self.backup(bundle)
            except Exception as ee:
                self.Debug("Failed again. {0}".format(ee))
                self.Debug("Disable backup mode.")
                self.backup_enable = False

    # recover whole content of envelope
    def recovery(self):
        filenames = os.listdir(self.temp_envelope_directory)
        for filename in filenames:
            # Open email envelope file
            with open("{0}{1}".format(self.temp_envelope_directory, filename), "r") as fe:
                try:
                    raw_data = fe.read()
                    data = json.loads(raw_data)
                    session = Session(None)
                    envelope = Envelope()

                    session.peer = data["session_peer"]
                    envelope.mail_from = data["envelope_mailfrom"]
                    envelope.rcpt_tos = [data["envelope_rcptto"]]
                    # Open email content file
                    with open("{0}{1}".format(self.temp_origin_directory, filename), "rb") as fo:
                        # read original email content
                        envelope.original_content = fo.read()

                    bundle = SMTPSessionBundle(data["corr_id"],
                        data["envelope_rcptto"],
                        None, session, envelope
                    )
                    self.SMTP_session_bundles[data["corr_id"]] = bundle

                    self.Debug("Recover from: {0} to: {1}".format(
                        data["envelope_mailfrom"],
                        data["envelope_rcptto"]
                    ), header=data["corr_id"])

                    # TODO: there is nothing in registered_users when restart
                    # Resend message
                    # TODO: Mysql to store user profile information
                    # Check if the receiver is registered
                    user_profile = self.registered_users.get(bundle.rcpt)

                    # TODO: Add corr_id to user's queuing_list

                    # Send message to MQ
                    self.send(bundle, user_profile=user_profile)
                except Exception as e:
                    print(e)

    def send(self, bundle, user_profile=None, direct=False):
        rcpt = "others"
        bundle = bundle
        user_profile = user_profile
        exchange_id = ""
        routing_key = "return"

        if not direct:
            # Check if the recepient is in registered_users list
            if user_profile and user_profile.service_ready:
                rcpt = bundle.rcpt
                bundle = bundle
                user_profile = user_profile
                exchange_id = "mail"
                routing_key = "mail.{0}".format(bundle.rcpt)

        self._send(
            rcpt=rcpt,
            bundle=bundle,
            user_profile=user_profile,
            exchange_id=exchange_id,
            routing_key=routing_key,
        )

    def _send(self, rcpt, bundle, user_profile, exchange_id, routing_key):
        # Check if the per user connection to MQ is established
        if rcpt not in self.MQ_handler_bundles:
            try:
                sender = sendmq.Sender(exchange_id=exchange_id,
                    routing_keys=[routing_key],
                    user_profile=user_profile,
                    host=self.MQ_host,
                    port=self.MQ_port,
                    silent_mode=True)
                self.MQ_handler_bundles[rcpt] = MQHandlerBundle(rcpt, sender)
            except Exception as e:
                # Wait for timeout_mod to resend
                self.Debug("Error occurred during sendmq Sender setup. {0}".format(e))
                return

        sender = self.MQ_handler_bundles[rcpt].sender

        # Send out message to MQ with corr_id
        ret = sender.send_msg(bundle.data, result=macro.PENDING, corr_id=bundle.corr_id)

        if ret:
            self.Debug("Send from: {0}, to: {1}".format(
                bundle.envelope.mail_from,
                bundle.rcpt
            ), header=bundle.corr_id)
        else:
            # Wait for timeout_mod to resend
            self.Debug("Failed to send message from: {0}, to: {1}".format(
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
                # including: each content of SMTPSessionBundle
                corr_id = str(uuid.uuid4())

                # Monitor list
                bundle = SMTPSessionBundle(corr_id, rcpt, server, session, envelope)
                self.SMTP_session_bundles[corr_id] = bundle

                # Doing backup here to prepare for error recovery
                if self.backup_enable:
                    self.backup(bundle)

                # Check if the receiver is using this service
                user_profile = self.registered_users.get(rcpt)

                # TODO: Add corr_id to user's queuing_list

                # Send message to MQ
                self.send(bundle, user_profile=user_profile)

                # Transform to return string
                result = "250 OK, saved as {0}".format(corr_id)

        except Exception as e:
            return "471 Something wrong happened, {0}".format(e)

        return result

    # STARTTLS Command
    # handle_STARTTLS(server, session, envelope)

    # EXCEPTION
    # handle_exception(error)

    # TODO: extend more action
    def apply_action(self, bundle, result, user_profile):
        # This handles the message that server send to itself
        try:
            if result["result"] == macro.PENDING:
                bundle.status = 0
                SMTP_result = self.send_email(bundle, user_profile)
            elif result["result"] == macro.PASS:
                bundle.status = 1
                SMTP_result = self.send_email(bundle, user_profile)
            elif result["result"] == macro.DENY:
                bundle.status = -1
                SMTP_result = (451, "Rejected by receiver's content filter, reason: {0}".
                    format(result["result"]))
            elif result["result"] == macro.SPAM:
                bundle.status = -1
                SMTP_result = (451, "Rejected by receiver's content filter, reason: {0}".
                    format(result["result"]))
            elif result["result"] == macro.VIRUS:
                bundle.status = -1
                SMTP_result = (451, "Rejected by receiver's content filter, reason: {0}".
                    format(result["result"]))
            elif result["result"] == macro.FORWARD:
                bundle.status = -1
                SMTP_result = (451, "Rejected by receiver's content filter, reason: {0}".
                    format(result["result"]))
            else:
                bundle.status = -1
                SMTP_result = (451, "Rejected by receiver's content filter, reason: {0}".
                    format(result["result"]))

            # Check result and update bundle status
            result = self.check_SMTP_result(bundle, SMTP_result)
        except KeyError as e:
            self.Debug("No such key {0} in client's response.".format(e), header=bundle.corr_id)

    # returnmq executor
    async def returnmq_executor(self):
        loop = asyncio.get_event_loop()
        while True:
            if len(self.SMTP_session_bundles) > 0:
                # Fetching result from MQ
                self.handler.check_result()

                # Get current waiting list
                waiting_list = list(self.handler.get_current_id())

                # Check if id in waiting list are all legal
                for corr_id in waiting_list:
                    # Fetching the emails
                    if corr_id in self.SMTP_session_bundles.keys():
                        _result = self.handler.get_result(corr_id)
                        result = json.loads(_result)
                    else:
                        self.handler.remove(corr_id)
                        continue

                    bundle = self.SMTP_session_bundles[corr_id]
                    user_profile = self.registered_users.get(bundle.rcpt)

                    self.Debug("Receive from: {0}, to: {1}".format(
                        bundle.envelope.mail_from, bundle.rcpt),header=corr_id
                    )

                    # Sol.1 Apply the action that client told us
                    #await self.apply_action(bundle, result, user_profile)

                    # Sol.2 Prepare subtask for loop
                    #subtasks.append(self.apply_action(bundle, result, user_profile))

                    # Sol.3
                    # TODO: maybe grouping by each users?
                    # https://docs.python.org/3/library/asyncio-dev.html#handle-blocking-functions-correctly
                    task = loop.run_in_executor(None, self.apply_action, bundle, result, user_profile)
                    self.subtasks.append(task)

                # Execute the subtask
                # Though it can asynchoronously execute the task
                # But it will still block until all tasks done
                await asyncio.gather(*self.subtasks)

            # run every 10*random secs
            await asyncio.sleep(random.random()*10)

    async def returnmq_mod(self):
        while True:
            try:
                self.handler = returnmq.Receiver(host=self.MQ_host,
                    port=self.MQ_port,
                    silent_mode=True
                )
                await self.returnmq_executor()
                break
            except asyncio.CancelledError:
                for subtask in self.subtasks:
                    subtask.cancel()
                break
            except Exception as e:
                for subtask in self.subtasks:
                    subtask.cancel()
                self.Debug("Error occurred during returnmq Receiver execution. {0}".format(e))
                self.Debug("Wait for restarting.")
                await asyncio.sleep(self.retry_interval)
                self.Debug("Restarting.")

    async def timeout_mod(self):
        while True:
            # run every 10*random secs
            await asyncio.sleep(random.random()*10)
            timestamp = int(time.time())

            # check if the mail have flush request
            while True:
                corr_id = self.flush.recv()
                if corr_id is not None:
                    bundle = self.SMTP_session_bundles[corr_id]
                    last_retry_timestamp = bundle.last_retry_timestamp
                    rcpt = bundle.rcpt
                    user_profile = self.registered_users.get(rcpt)

                    self.send(bundle, user_profile=user_profile, direct=False)
                    bundle.last_retry_timestamp = timestamp
                else:
                    break

            # run through every monitored emails
            for corr_id in self.SMTP_session_bundles:
                bundle = self.SMTP_session_bundles[corr_id]
                last_retry_timestamp = bundle.last_retry_timestamp
                rcpt = bundle.rcpt
                user_profile = self.registered_users.get(rcpt)

                # using default timeout if no user settings
                if user_profile and user_profile.service_ready:
                    timeout = user_profile.timeout * 2
                # reset timeout, *2 means to wait for MQ Message timeout first
                else:
                    timeout = self.config.kwargs["timeout"] * 2

                # check if time is up
                if timestamp - last_retry_timestamp > timeout:
                    self.send(bundle, user_profile=user_profile, direct=True)
                    bundle.last_retry_timestamp = timestamp
