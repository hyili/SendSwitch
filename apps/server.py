#!/usr/bin/env python3

import sys
import time
import random
import asyncio
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Proxy

sys.path.append("../modules/")
from handler import MQHandler
from config_loader import Config
import web
import user_profile

# http://aiosmtpd.readthedocs.io/en/latest/aiosmtpd/docs/controller.html?highlight=8025#controller-api
# Asynchronous smtpd server, await many functions to handle the request at the
# same time

def Create_MQController(config, local, remote, silent_mode=False,
    returnmq_mod=True, statistic_mod=True, timeout_mod=True):

    hostname = config.nodes[local]["hostname"]
    port = config.nodes[local]["port"]
    remote_hostname = config.nodes[remote]["hostname"]
    remote_port = config.nodes[remote]["port"]

    # SMTP method handler
    handler = MQHandler(config=config,
        remote_hostname=remote_hostname,
        remote_port=remote_port,
        silent_mode=silent_mode)

    # Return message handler (From MessageQueue)
    loop = asyncio.new_event_loop()
    if returnmq_mod:
        loop.create_task(handler.returnmq_mod())

    if statistic_mod:
        loop.create_task(handler.statistic_mod())

    if timeout_mod:
        loop.create_task(handler.timeout_mod())

    # SMTP server setup
    SMTPDController = Controller(
        handler=handler,
        loop=loop,
        hostname=hostname,
        port=port)

    return SMTPDController

def Create_ProxyController(config, local, remote):
    hostname = config.nodes[local]["hostname"]
    port = config.nodes[local]["port"]
    remote_hostname = config.nodes[remote]["hostname"]
    remote_port = config.nodes[remote]["port"]

    # SMTP method handler
    handler = Proxy(remote_hostname=remote_hostname,
        remote_port=remote_port)

    # SMTP server setup
    SMTPDController = Controller(
        handler=handler,
        hostname=hostname,
        port=port)

    return SMTPDController

users = user_profile.Users()
config = Config(("Message-Queue-node", "localhost", 8025),
    ("Amavisd-new-node", "localhost", 8026),
    ("Postfix", "localhost", 10026),
    registered_users=users)

SMTPD_MQController = Create_MQController(config=config,
    local="Message-Queue-node", remote="Postfix")

SMTPD_ProxyController = Create_ProxyController(config=config,
    local="Amavisd-new-node", remote="Postfix")

try:
    print(" [*] Waiting for emails. To exit press CTRL+C")
    SMTPD_MQController.start()
    SMTPD_ProxyController.start()
    web.ManagementUI(config)

#    # Do nothing here
#    while True:
#        time.sleep(random.random())

    print(" [*] Quit.")
    SMTPD_MQController.stop()
    SMTPD_ProxyController.stop()
except KeyboardInterrupt:
    print(" [*] Signal Catched. Quit.")
    SMTPD_MQController.stop()
    SMTPD_ProxyController.stop()
except Exception as e:
    print(e)
    SMTPD_MQController.stop()
    SMTPD_ProxyController.stop()
