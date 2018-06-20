#!/usr/bin/env python3

import sys
import time
import random
import asyncio
from aiosmtpd.handlers import Proxy

sys.path.append("../modules/server-side")
from handler import MQHandler, ProxyHandler
from controller import Server_Controller
import web

sys.path.append("../config")
import server_config

# http://aiosmtpd.readthedocs.io/en/latest/aiosmtpd/docs/controller.html?highlight=8025#controller-api
# Asynchronous smtpd server, await many functions to handle the request at the
# same time

def Create_MQController(config, local, remote, backup_enable, temp_directory, silent_mode,
    returnmq_mod=True, statistic_mod=True, timeout_mod=True):

    # SMTP method handler
    handler = MQHandler(config=config,
        local=local,
        remote=remote,
        backup_enable=backup_enable,
        temp_directory=temp_directory,
        silent_mode=silent_mode)

    # Return message handler (From MessageQueue)
    loop = asyncio.new_event_loop()
    if returnmq_mod:
        loop.create_task(handler.returnmq_mod())

    if timeout_mod:
        loop.create_task(handler.timeout_mod())

    # SMTP server setup
    SMTPDController = Server_Controller(
        handler=handler,
        loop=loop,
        hostname=local.hostname,
        port=local.port)

    return SMTPDController

def Create_ProxyController(config, local, remote, silent_mode):
    # SMTP method handler
    handler = ProxyHandler(config=config,
        local=local,
        remote=remote,
        silent_mode=silent_mode)

    # SMTP server setup
    SMTPDController = Server_Controller(
        handler=handler,
        hostname=local.hostname,
        port=local.port)

    return SMTPDController

# Config setup
config = server_config.config

servers = config.kwargs["registered_servers"]
users = config.kwargs["registered_users"]
default_user_settings = users.getDefault()
backup_enable = config.kwargs["backup_enable"]
temp_directory = config.kwargs["temp_directory"]
silent_mode = config.kwargs["silent_mode"]

# Controller setup
# TODO: auto-creation according to config
MQ_node = "Message-Queue-node"
SMTPD_MQController = Create_MQController(config=config,
    local=servers.get(MQ_node),
    remote=servers.get(default_user_settings[MQ_node]),
    backup_enable=backup_enable,
    temp_directory=temp_directory,
    silent_mode=silent_mode
)

SMTPD_ProxyControllers = list()
server_ids = list(default_user_settings.keys())
server_ids.remove(MQ_node)
for server_id in server_ids:
    try:
        next_hop_server_id = default_user_settings[server_id]
    except Exception as e:
        print(" [*] {0}".format(e))
        quit()
    finally:
        SMTPD_ProxyControllers.append(
            Create_ProxyController(config=config,
                local=servers.get(server_id),
                remote=servers.get(next_hop_server_id),
                silent_mode=silent_mode
            )
        )

try:
    print(" [*] Waiting for emails. To exit press CTRL+C")

    # Need to start proxy first
    for SMTPD_ProxyController in SMTPD_ProxyControllers:
        SMTPD_ProxyController.start()
    SMTPD_MQController.start()
    web.ManagementUI(config)

    print(" [*] Quit.")
    SMTPD_MQController.stop()
    for SMTPD_ProxyController in SMTPD_ProxyControllers:
        SMTPD_ProxyController.stop()
except KeyboardInterrupt:
    print(" [*] Signal Catched. Quit.")
    SMTPD_MQController.stop()
    for SMTPD_ProxyController in SMTPD_ProxyControllers:
        SMTPD_ProxyController.stop()
except Exception as e:
    print(" [*] {0}".format(e))
    SMTPD_MQController.stop()
    for SMTPD_ProxyController in SMTPD_ProxyControllers:
        SMTPD_ProxyController.stop()
