#!/usr/bin/env python3
# http://aiosmtpd.readthedocs.io/en/latest/aiosmtpd/docs/smtp.html
# https://github.com/aio-libs/aiosmtpd

import os
import re
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
import email
from email import policy

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
SUBJECT = re.compile(br"(\r\n|\r|\n)(subject:)(.*)(\r\n|\r|\n)", re.IGNORECASE)
TO = re.compile(br"(\r\n|\r|\n)(to:)(.*)(\r\n|\r|\n)", re.IGNORECASE)

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
        self.timeout_retried = False
        self.timeout_retried_times = 0
        self.server = server
        self.session = session
        self.envelope = copy.deepcopy(envelope)
        self.envelope.rcpt_tos = [rcpt]
        self.data = self.email_translator(self.envelope.original_content)
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
        self.processing_mails = config.kwargs["processing_mails"]
        self.logger = config.kwargs["logger"]

        self.silent_mode = silent_mode
        self.SMTP_session_bundles = {}

        # logging
        self.output = config.kwargs["output"]

    def Debug(self, msg, header="*", bundle=None):
        if not self.silent_mode:
            timestamp = str(datetime.datetime.utcnow())
            self.logger.info(" [{0:25s}] {1:36s}, {2:26s}, {3:s}".format(self.current_server.sid, header, timestamp, msg))
            self.output.send((" [{0:25s}] {1:36s}, {2:26s}, {3:s}".format(self.current_server.sid, header, timestamp, msg), bundle))

    def check_SMTP_session_bundle(self, bundle, SMTP_result):
        # Check if sending operation went wrong
        if bundle.status >= 0:
            if SMTP_result[0] == 250:
                self.Debug("Successfully sent out, reason: {0}.".format(SMTP_result), header=bundle.corr_id, bundle=bundle)

                return (250, "OK saved as {0}, next hop status {1}.".format(bundle.corr_id, str(SMTP_result)))
            elif SMTP_result[0] < 0:
                self.Debug("Something wrong happened during check_SMTP_session_bundle(), reason: {0}.".
                    format(SMTP_result), header=bundle.corr_id)

                return (471, "Something wrong happened to {0}, next hop status {1}".format(bundle.corr_id, str(SMTP_result)))
            else:
                self.Debug("Something wrong happened during check_SMTP_session_bundle(), reason: {0}.".
                    format(SMTP_result), header=bundle.corr_id)

                return (471, "Something wrong happened to {0}, next hop status {1}".format(bundle.corr_id, str(SMTP_result)))
        else:
            self.Debug("Remove it, reason: {0}".format(SMTP_result), header=bundle.corr_id, bundle=bundle)

            return (250, "OK removed.")

    def finish(self, corr_id):
        bundle = self.SMTP_session_bundles.pop(corr_id, None)

        user = self.registered_users.get(bundle.rcpt)
        # TODO: current Do not need this
        #self.processing_mails.updateMail(corr_id, -1)

    def send_email(self, bundle, user):
        try:
            # get next hostname and port according to user's settings
            next_hop_server_sid = self.next_hop_server.sid
            next_hop_server_hostname = self.next_hop_server.hostname
            next_hop_server_port = self.next_hop_server.port

            if user and user.route_ready:
                user_route = self.registered_user_routes.get(user.id, self.current_server.id)
                if user_route:
                    next_hop_server_sid = user_route.dst.sid
                    next_hop_server_hostname = user_route.dst.hostname
                    next_hop_server_port = user_route.dst.port

            self.Debug("Next hop id: {0}, host: {1}, port: {2}.".
                format(next_hop_server_sid, next_hop_server_hostname, next_hop_server_port),
                header=bundle.corr_id, bundle=bundle
            )

            content = bundle.envelope.original_content
            peer = bundle.session.peer[0].encode("ascii")
            data = b"X-SendSwitch-Peer: %s%s%s" % (peer, CRLF, content)

            refused = self._send_email(bundle, data, next_hop_server_hostname, next_hop_server_port)
        except Exception as e:
            self.Debug("Something wrong happened during send_email(), reason: {0}.".format(e), header=bundle.corr_id)
            refused = {bundle.rcpt: (471, "Failed, reason: Internal error occurred.")}
        finally:
            # TODO: this will have problem when group mailing is implemented
            return refused[bundle.rcpt]

    def _send_email(self, bundle, data, next_hop_server_hostname, next_hop_server_port):
        refused = {}
        mail_from = bundle.envelope.mail_from
        rcpt_tos = bundle.envelope.rcpt_tos

        try:
            s = smtplib.SMTP()
            s.connect(next_hop_server_hostname, next_hop_server_port)
            try:
                # TODO: This won't return message after DATA command, though it is well-defined with SMTPUTF8
                #msg = email.message_from_bytes(data)
                #refused[rcpt_tos[0]] = 250, s.send_message(msg, from_addr=mail_from, to_addrs=rcpt_tos)

                # Though s.sendmail can done almost everything, it cannot get the reply
                s.docmd("HELO {0}".format(self.config.kwargs["host_domain"]))
                s.docmd("MAIL FROM:", "{0}".format(mail_from))
                for rcpt in rcpt_tos:
                    s.docmd("RCPT TO:", "{0}".format(rcpt))
                s.docmd("DATA")
                s.send(data)
                s.send("\r\n.\r\n")
                reply = s.getreply()
                for rcpt in rcpt_tos:
                    refused[rcpt] = (reply[0], str(reply[1].decode("utf-8", errors="replace")))
            except UnicodeEncodeError as e:
                msg = email.message_from_bytes(data, policy=policy.SMTPUTF8)
                for rcpt in rcpt_tos:
                    refused[rcpt] = 250, s.send_message(msg, from_addr=mail_from, to_addrs=rcpt, mail_options=["SMTPUTF8"])
            except smtplib.SMTPRecipientsRefused as e:
                self.Debug("Something wrong happened during _send_email(), reason: {0}.".format(e), header=bundle.corr_id)
                refused = e.recipients
            except smtplib.SMTPException as e:
                self.Debug("Something wrong happened during _send_email(), reason: {0}.".format(e), header=bundle.corr_id)
                # All recipients were refused.  If the exception had an associated
                # error code, use it.  Otherwise, fake it with a non-triggering
                # exception code.
                errcode = getattr(e, "smtp_code", -1)
                errmsg = getattr(e, "smtp_error", str(e))
                for rcpt in rcpt_tos:
                    refused[rcpt] = (errcode, errmsg)
            except Exception as e:
                self.Debug("Something wrong happened during _send_email(), reason: {0}.".format(e), header=bundle.corr_id)
                errcode = getattr(e, "smtp_code", str(e)) if hasattr(e, "smtp_code") else -2
                errmsg = getattr(e, "smtp_error", str(e)) if hasattr(e, "smtp_error") else str(e)
                for rcpt in rcpt_tos:
                    refused[rcpt] = (errcode, errmsg)
            finally:
                s.quit()
        except Exception as e:
            self.Debug("Something wrong happened during _send_email(), reason: {0}.".format(e), header=bundle.corr_id)
            errcode = getattr(e, "smtp_code", str(e)) if hasattr(e, "smtp_code") else -2
            errmsg = getattr(e, "smtp_error", str(e)) if hasattr(e, "smtp_error") else str(e)
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

                self.Debug("Received from SMTP. from: {0}, to: {1}".\
                    format(bundle.envelope.mail_from, bundle.rcpt),
                    header=corr_id, bundle=bundle
                )

                # Check if the receiver is registered
                user = self.registered_users.get(rcpt)
                # TODO: current Do not need this
                #self.processing_mails.add(user.id, corr_id)

                # Send message to next hop, run_in_executor to prevent blocking
                loop = asyncio.get_event_loop()
                task = loop.run_in_executor(None, self.send_email, bundle, user)
                finished, pending = await asyncio.wait([task])
                for r in finished:
                    SMTP_result = r.result()

                # Check result
                result = self.check_SMTP_session_bundle(bundle, SMTP_result)

                # Pop finished job from SMTP_session_bundles
                self.finish(bundle.corr_id)

        except Exception as e:
            return "471 Something wrong happened, {0}".format(e)

        return "{0} {1}".format(result[0], result[1])

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
            self.Debug("Something wrong happened during init(), reason: {0}.".format(e))
            self.Debug("Disable backup mode.")
            self.backup_enable = False

    def finish(self, corr_id):
        bundle = self.SMTP_session_bundles.pop(corr_id, None)

        if self.backup_enable:
            try:
                os.remove("{0}{1}".format(self.temp_envelope_directory, bundle.corr_id))
                os.remove("{0}{1}".format(self.temp_origin_directory, bundle.corr_id))
                self.Debug("Removed.", header=corr_id)
            except Exception as e:
                self.Debug("Something wrong happened during finish(), reason: {0}.".format(e), header=corr_id)

        user = self.registered_users.get(bundle.rcpt)
        # TODO: current
        self.processing_mails.updateMail(corr_id, -1)

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

                self.Debug("Backuped.", header=data["corr_id"])
        except Exception as e:
            self.Debug("Something wrong happened during backup(), reason: {0}.".format(e), header=data["corr_id"])
            self.Debug("Reinitialize.")
            try:
                self.init()
                self.backup(bundle)
            except Exception as ee:
                self.Debug("Failed again after reinitialization. {0}".format(ee), header=data["corr_id"])
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

                    self.Debug("Recovered. from: {0} to: {1}.".format(
                        data["envelope_mailfrom"],
                        data["envelope_rcptto"]
                    ), header=data["corr_id"], bundle=bundle)

                    # TODO: there is nothing in registered_users when restart
                    # Resend message
                    # TODO: Mysql to store user profile information
                    # Check if the receiver is registered
                    user = self.registered_users.get(bundle.rcpt)

                    # Send message to MQ
                    self.send(bundle, user=user)
                except Exception as e:
                    self.Debug("Something wrong happened during recovery(), reason: {0}.".format(e), header=filename)

    def send(self, bundle, user=None, direct=False):
        rcpt = "others"
        bundle = bundle
        user = user
        exchange_id = ""
        routing_key = "return"

        if not direct:
            # Check if the recepient is in registered_users list
            if user and user.service_ready:
                rcpt = bundle.rcpt
                bundle = bundle
                user = user
                exchange_id = "mail"
                routing_key = "mail.{0}".format(bundle.rcpt)

        self._send(
            rcpt=rcpt,
            bundle=bundle,
            user=user,
            exchange_id=exchange_id,
            routing_key=routing_key,
        )

    def _send(self, rcpt, bundle, user, exchange_id, routing_key):
        # Check if the per user connection to MQ is established
        if rcpt not in self.MQ_handler_bundles:
            try:
                sender = sendmq.Sender(exchange_id=exchange_id,
                    routing_keys=[routing_key],
                    user=user,
                    host=self.MQ_host,
                    port=self.MQ_port,
                    logger=self.logger,
                    silent_mode=True
                )
                self.MQ_handler_bundles[rcpt] = MQHandlerBundle(rcpt, sender)
            except Exception as e:
                # Wait for timeout_mod to resend
                self.Debug("Something wrong happened during _send(), reason: {0}.".format(e), header=bundle.corr_id)
                return

        sender = self.MQ_handler_bundles[rcpt].sender

        # Send out message to MQ with corr_id
        ret = sender.send_msg(bundle.data, action=macro.TAG_NOTHING, result=macro.ACTION_DEFAULT, corr_id=bundle.corr_id)

        if ret:
            self.Debug("Sent to MessageQueue.", header=bundle.corr_id, bundle=bundle)
        else:
            # Wait for timeout_mod to resend
            self.Debug("Failed to send to MessageQueue.", header=bundle.corr_id, bundle=bundle)

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

                self.Debug("Received from SMTP. from: {0}, to: {1}".\
                    format(bundle.envelope.mail_from, bundle.rcpt),
                    header=corr_id, bundle=bundle
                )

                # Doing backup here to prepare for error recovery
                if self.backup_enable:
                    self.backup(bundle)

                # Check if the receiver is using this service
                user = self.registered_users.get(rcpt)
                # TODO: current
                self.processing_mails.add(user.id, corr_id)

                # Send message to MQ
                self.send(bundle, user=user)

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
    def apply_action(self, bundle, result, user):
        # This handles the message that server send to itself
        try:
            # Pre apply ACTION to the email
            # ACTION_DELAY
            if result["action"]["id"] & macro.ACTION_DELAY:
                timestamp = int(time.time())

                bundle.timeout_retried = False
                bundle.last_retry_timestamp = timestamp
                self.Debug("Wait for resend, reason: ACTION_DELAY ({0}).".format(result["result"]["reason"]), header=bundle.corr_id, bundle=bundle)

                # Gen result
                result = (471, "Wait for resend, reason: ACTION_DELAY")

                # Return directly
                return

            # TAG the email, can use multiple tags here
            # TAG_NOTHING
            if result["result"]["id"] & macro.TAG_NOTHING:
                pass
            # TAG_SPAM
            if result["result"]["id"] & macro.TAG_SPAM:
                bundle.envelope.original_content = re.sub(SUBJECT, br"\1\2 ***SPAM***\3\4", bundle.envelope.original_content, count=1)
                self.Debug("Tag it SPAM, reason: TAG_SPAM.", header=bundle.corr_id, bundle=bundle)
            # TAG_VIRUS
            if result["result"]["id"] & macro.TAG_VIRUS:
                bundle.envelope.original_content = re.sub(SUBJECT, br"\1\2 ***VIRUS***\3\4", bundle.envelope.original_content, count=1)
                self.Debug("Tag it VIRUS, reason: TAG_VIRUS.", header=bundle.corr_id, bundle=bundle)

            # Post apply ACTION to the email, can only apply one action
            # ACTION_DEFAULT
            if result["action"]["id"] & macro.ACTION_DEFAULT:
                bundle.status = 0
                SMTP_result = self.send_email(bundle, user)
                self.Debug("Send to {0}, reason: ACTION_DEFAULT ({1}).".format(bundle.rcpt, result["result"]["reason"]), header=bundle.corr_id, bundle=bundle)

                # Check result and update bundle status
                result = self.check_SMTP_session_bundle(bundle, SMTP_result)
            # ACTION_PASS
            elif result["action"]["id"] & macro.ACTION_PASS:
                bundle.status = 1
                SMTP_result = self.send_email(bundle, user)
                self.Debug("Send to {0}, reason: ACTION_PASS ({1}).".format(bundle.rcpt, result["result"]["reason"]), header=bundle.corr_id, bundle=bundle)

                # Check result and update bundle status
                result = self.check_SMTP_session_bundle(bundle, SMTP_result)
            # ACTION_DENY
            elif result["action"]["id"] & macro.ACTION_DENY:
                self.Debug("Remove it, reason: ACTION_DENY ({0}).".format(result["result"]["reason"]), header=bundle.corr_id, bundle=bundle)

                # Gen result
                result = (451, "Rejected by receiver's content filter, reason: ACTION_DENY")
            # ACTION_FORWARD
            elif result["action"]["id"] & macro.ACTION_FORWARD:
                if "forward" in result["action"]:
                    # Reset receiver's information
                    bundle.rcpt = result["action"]["forward"]
                    bundle.envelope.rcpt_tos = [result["action"]["forward"]]

                    bundle.status = 1
                    SMTP_result = self.send_email(bundle, None)
                    self.Debug("Forward to {0}, reason: ACTION_FORWARD ({1}).".format(result["action"]["forward"], result["result"]["reason"]), header=bundle.corr_id, bundle=bundle)
                else:
                    bundle.status = 1
                    SMTP_result = self.send_email(bundle, user)
                    self.Debug("Fall back to ACTION_PASS, reason: ACTION_FORWARD with no forward address.", header=bundle.corr_id, bundle=bundle)

                # Check result and update bundle status
                result = self.check_SMTP_session_bundle(bundle, SMTP_result)
            # ACTION_QUARATINE
            elif result["action"]["id"] & macro.ACTION_QUARANTINE:
                self.Debug("Remove it, reason: Not implement ACTION_QUARATINE.", header=bundle.corr_id, bundle=bundle)

                # Gen result
                result = (451, "Rejected by receiver's content filter, reason: ACTION_QUARATINE (NOT IMPLEMENT)")
            # OTHERS
            else:
                self.Debug("Remove it, reason: Unknown action code {0}.".format(result["action"]["id"]), header=bundle.corr_id, bundle=bundle)
                result = (451, "Rejected by receiver's content filter, reason: Unknown action code {0}.".format(result["action"]["id"]))

            # Pop finished job from SMTP_session_bundles
            self.finish(bundle.corr_id)
        except KeyError as e:
            self.Debug("No such key {0} in client's response.".format(e), header=bundle.corr_id)
        except Exception as e:
            self.Debug("Something wrong happened during apply_action(), reason: {0}.".format(e), header=bundle.corr_id)

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
                        bundle = self.SMTP_session_bundles[corr_id]

                        # Check if return messages' publisher correct
                        _result, routing_key = self.handler.get_result(corr_id)
                        if routing_key != "mail.{0}".format(bundle.rcpt) and routing_key != "return":
                            self.Debug("Catch an unusual message with routing_key \'{0}\'.".format(routing_key), header=corr_id)
                            continue

                        result = json.loads(_result)
                        self.Debug("Received from MessageQueue.", header=corr_id, bundle=bundle)

                        # TODO: MySQL query flood issue
                        user = self.registered_users.get(bundle.rcpt)

                        # Sol.1 Apply the action that client told us
                        #await self.apply_action(bundle, result, user)

                        # Sol.2 Prepare subtask for loop
                        #subtasks.append(self.apply_action(bundle, result, user))

                        # Sol.3
                        # TODO: maybe grouping by each users?
                        # https://docs.python.org/3/library/asyncio-dev.html#handle-blocking-functions-correctly
                        task = loop.run_in_executor(None, self.apply_action, bundle, result, user)
                        self.subtasks.append(task)
                    else:
                        # Remove this spam message, and return routing_key for logging
                        _result, routing_key = self.handler.get_result(corr_id)
                        self.Debug("Catch an spam message with routing_key {0}.".format(routing_key), header=corr_id)
                        continue

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
                    logger=self.logger,
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
                self.Debug("Something wrong happened during returnmq_mod(), reason: {0}.".format(e))
                self.Debug("Wait for restarting.")
                await asyncio.sleep(self.retry_interval)
                self.Debug("Restarting.")

    async def timeout_mod(self):
        while True:
            try:
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
                        user = self.registered_users.get(rcpt)

                        self.send(bundle, user=user, direct=False)
                        bundle.last_retry_timestamp = timestamp
                    else:
                        break

                # TODO: DB query optimization
                # run through every monitored emails
                for corr_id in self.SMTP_session_bundles:
                    bundle = self.SMTP_session_bundles[corr_id]
                    last_retry_timestamp = bundle.last_retry_timestamp
                    rcpt = bundle.rcpt
                    user = self.registered_users.get(rcpt)

                    # using default timeout if no user settings
                    if user and user.service_ready:
                        timeout = user.timeout * 2
                    # reset timeout, *2 means to wait for MQ Message timeout first
                    else:
                        timeout = self.config.kwargs["timeout"] * 2

                    # check if time is up
                    if timestamp - last_retry_timestamp > timeout:
                        if bundle.timeout_retried or bundle.timeout_retried_times > 10:
                            self.send(bundle, user=user, direct=True)
                            bundle.last_retry_timestamp = timestamp
                        else:
                            self.send(bundle, user=user, direct=False)
                            bundle.last_retry_timestamp = timestamp
                            bundle.timeout_retried_times += 1
                            bundle.timeout_retried = True
            except asyncio.CancelledError:
                for subtask in self.subtasks:
                    subtask.cancel()
                break
            except Exception as e:
                self.Debug("Something wrong happened during returnmq_mod(), reason: {0}.".format(e))
