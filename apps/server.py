#!/usr/bin/env python3

import sys
import time
import random
import asyncio
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Proxy

sys.path.append("../modules/")
from handler import MQHandler, ProxyHandler
from config_loader import Config
from output import Output
import web
import user_profile
import server_profile

# http://aiosmtpd.readthedocs.io/en/latest/aiosmtpd/docs/controller.html?highlight=8025#controller-api
# Asynchronous smtpd server, await many functions to handle the request at the
# same time

def Create_MQController(config, local, remote, silent_mode=False,
    returnmq_mod=True, statistic_mod=True, timeout_mod=True):

    # SMTP method handler
    handler = MQHandler(config=config,
        local=local,
        remote=remote,
        silent_mode=silent_mode)

    # Return message handler (From MessageQueue)
    loop = asyncio.new_event_loop()
    if returnmq_mod:
        loop.create_task(handler.returnmq_mod())

    if timeout_mod:
        loop.create_task(handler.timeout_mod())

    # SMTP server setup
    SMTPDController = Controller(
        handler=handler,
        loop=loop,
        hostname=local.hostname,
        port=local.port)

    return SMTPDController

def Create_ProxyController(config, local, remote, silent_mode=False):
    # SMTP method handler
    handler = ProxyHandler(config=config,
        local=local,
        remote=remote,
        silent_mode=silent_mode)

    # SMTP server setup
    SMTPDController = Controller(
        handler=handler,
        hostname=local.hostname,
        port=local.port)

    return SMTPDController

# Server setup
servers = server_profile.Servers()
servers.add("Message-Queue-node", "localhost", 8025)
servers.add("Amavisd-new-node", "localhost", 8026)
servers.add("Postfix", "localhost", 10026)
servers.add("Noop", "localhost", 10000)
servers.add("CS", "mail.cs.nctu.edu.tw", 25)

# Check servers
for id in servers.getAll():
    server = servers.get(id)
    print(" [*] Server Settings OK: id: \"{0}\", hostname: \"{1}\", port: {2}".
        format(server.id, server.hostname, server.port))

# Server next hop setup
default_settings = {
    "Message-Queue-node": "Amavisd-new-node",
    "Amavisd-new-node": "Postfix"
}

# Check settings are correct
for key in default_settings:
    if servers.get(key) is None:
        raise(Exception(" [*] default_settings: \"{0}\" not in servers".
            format(key)))
    if servers.get(default_settings[key]) is None:
        raise(Exception(" [*] default_settings: \"{0}\" not in servers".
            format(default_settings[key])))

    print(" [*] Route Settings OK: from: \"{0}\" to: \"{1}\"".
        format(key, default_settings[key]))

# User setup with default route settings
users = user_profile.Users(settings=default_settings)

# Output setup
output = Output()

# LDAP settings
ldap_settings = dict()
ldap_settings["use_ssl"] = False
ldap_settings["user_dn"] = "uid={0},dc=hyili,dc=idv,dc=tw"
ldap_settings["ldap_server"] = "localhost"

# Config setup
config = Config(registered_servers=servers,
    registered_users=users,
    email_domain="hyili.idv.tw",
    host_domain="hyili.idv.tw",
    timeout=60,
    output=output,
    ldap_settings=ldap_settings)

# Controller setup
SMTPD_MQController = Create_MQController(config=config,
    local=servers.get("Message-Queue-node"),
    remote=servers.get(default_settings["Message-Queue-node"]))

SMTPD_ProxyController = Create_ProxyController(config=config,
    local=servers.get("Amavisd-new-node"),
    remote=servers.get(default_settings["Amavisd-new-node"]))

try:
    print(" [*] Waiting for emails. To exit press CTRL+C")

    # Need to reverse the order of server start
    # Due to default_settings
    SMTPD_ProxyController.start()
    SMTPD_MQController.start()
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
