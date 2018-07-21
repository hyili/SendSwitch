#!/usr/bin/env python3

import sys
import time
import random
import asyncio
from aiosmtpd.handlers import Proxy

sys.path.append("../modules/share")
sys.path.append("../modules/server-side")
sys.path.append("../modules/MessageQueue")
from handler import SMTPMQHandler, SMTPProxyHandler
from controller import ServerController
from web import web

sys.path.append("../config")
import server_config

# http://aiosmtpd.readthedocs.io/en/latest/aiosmtpd/docs/controller.html?highlight=8025#controller-api
# Asynchronous smtpd server, await many functions to handle the request at the
# same time

def create_MQ_controller(config, current_server, next_hop_server, backup_enable, temp_directory, silent_mode,
    returnmq_mod=True, timeout_mod=True):

    # SMTP method handler
    handler = SMTPMQHandler(config=config,
        current_server=current_server,
        next_hop_server=next_hop_server,
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
    SMTPDController = ServerController(
        handler=handler,
        loop=loop,
        hostname=current_server.hostname,
        port=current_server.port)

    return SMTPDController

def create_proxy_controller(config, current_server, next_hop_server, silent_mode):
    # SMTP method handler
    handler = SMTPProxyHandler(config=config,
        current_server=current_server,
        next_hop_server=next_hop_server,
        silent_mode=silent_mode)

    # SMTP server setup
    SMTPDController = ServerController(
        handler=handler,
        hostname=current_server.hostname,
        port=current_server.port)

    return SMTPDController

# Config setup
config = server_config.config

servers = config.kwargs["registered_servers"]
users = config.kwargs["registered_users"]
logger = config.kwargs["logger"]
default_user_routes = config.kwargs["default_user_routes"]
backup_enable = config.kwargs["backup_enable"]
temp_directory = config.kwargs["temp_directory"]
silent_mode = config.kwargs["silent_mode"]

# Controller setup
MQ_node = "Message-Queue-node"
SMTPD_MQ_controller = create_MQ_controller(config=config,
    current_server=servers.get(MQ_node),
    next_hop_server=servers.get(default_user_routes[MQ_node]),
    backup_enable=backup_enable,
    temp_directory=temp_directory,
    silent_mode=silent_mode
)

SMTPD_proxy_controllers = list()
server_ids = list(default_user_routes.keys())
server_ids.remove(MQ_node)
for server_id in server_ids:
    try:
        next_hop_server_id = default_user_routes[server_id]
    except Exception as e:
        logger.info(" [*] {0}".format(e))
        quit()
    finally:
        SMTPD_proxy_controllers.append(
            create_proxy_controller(config=config,
                current_server=servers.get(server_id),
                next_hop_server=servers.get(next_hop_server_id),
                silent_mode=silent_mode
            )
        )

try:
    logger.info(" [*] Waiting for emails. To exit press CTRL+C")

    # Need to start proxy first
    for SMTPD_proxy_controller in SMTPD_proxy_controllers:
        SMTPD_proxy_controller.start()
    SMTPD_MQ_controller.start()
    web.ManagementUI(config)

    logger.info(" [*] Quit.")
    SMTPD_MQ_controller.stop()
    for SMTPD_proxy_controller in SMTPD_proxy_controllers:
        SMTPD_proxy_controller.stop()
except KeyboardInterrupt:
    logger.info(" [*] Signal Catched. Quit.")
    SMTPD_MQ_controller.stop()
    for SMTPD_proxy_controller in SMTPD_proxy_controllers:
        SMTPD_proxy_controller.stop()
except Exception as e:
    logger.info(" [*] {0}".format(e))
    SMTPD_MQ_controller.stop()
    for SMTPD_proxy_controller in SMTPD_proxy_controllers:
        SMTPD_proxy_controller.stop()
