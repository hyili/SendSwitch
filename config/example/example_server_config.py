#!/usr/bin/env python3

import logging

from config_loader import Config
from shared_queue import SharedQueue
from model import user_profile, server_profile, user_route, server_route

# DB setup
db_host = "localhost"
db_port = 3306
db_name = "db_name"
db_user = "db_user"
db_passwd = "db_passwd"

# Logger setup
logger = logging.getLogger("Application-Logger")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("/tmp/PSF.log")
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# TODO: formatter here
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Server setup
servers = server_profile.Servers(logger=logger, db_host=db_host, db_port=db_port, db_name=db_name,
    db_user=db_user, db_passwd=db_passwd)

# For Postfix to inject email
Pi = servers.get("Postfix-incoming-node")
if not Pi:
    Pi = servers.add(sid="Postfix-incoming-node", hostname="localhost", port=8025, dest=False)
# For Postfix to eject email
Po = servers.get("Postfix-outgoing-node")
if not Po:
    Po = servers.add(sid="Postfix-outgoing-node", hostname="localhost", port=10025, source=False)

# For Amavisd-new to inject email
Ai = servers.get("Amavisd-new-incoming-node")
if not Ai:
    Ai = servers.add(sid="Amavisd-new-incoming-node", hostname="localhost", port=8024, dest=False)
# For Amavisd-new to eject email
Ao = servers.get("Amavisd-new-outgoing-node")
if not Ao:
    Ao = servers.add(sid="Amavisd-new-outgoing-node", hostname="localhost", port=10024, source=False)

# Message Queue node
MQ = servers.get("Message-Queue-node")
if not MQ:
    MQ = servers.add(sid="Message-Queue-node", hostname="localhost", port=8026)

# Server next hop setup
default_user_routes = {
    "Postfix-incoming-node": "Postfix-outgoing-node",
    "Message-Queue-node": "Postfix-outgoing-node",
    "Amavisd-new-incoming-node": "Postfix-outgoing-node"
}

# Server Route setup
server_routes = server_route.ServerRoutes(logger=logger, db_host=db_host, db_port=db_port,
    db_name=db_name, db_user=db_user, db_passwd=db_passwd)

server_routes.add(Ao.id, Ai.id)

# User setup with default route settings
users = user_profile.Users(logger=logger, db_host=db_host, db_port=db_port, db_name=db_name,
    db_user=db_user, db_passwd=db_passwd)

# User Route setup
user_routes = user_route.UserRoutes(logger=logger, db_host=db_host, db_port=db_port,
    db_name=db_name, db_user=db_user, db_passwd=db_passwd)

# LDAP settings
ldap_settings = dict()
ldap_settings["use_ssl"] = False
ldap_settings["user_dn"] = "uid={0},dc=,dc=,dc="
ldap_settings["ldap_server"] = "localhost"

# Output setup
output = SharedQueue()

# Flush setup
flush = SharedQueue()

# Config setup
config = Config(framework_name="framework_name",
    registered_servers=servers,
    registered_server_routes=server_routes,
    registered_users=users,
    registered_user_routes=user_routes,
    logger=logger,
    email_domain="hyili.idv.tw",
    host_domain="hyili.idv.tw",
    MQ_host="localhost",
    MQ_port=5672,
    web_host="localhost",
    web_port=60666,
    web_secret_key="Th151553cr3tK3y",
    timeout=60,
    retry_interval=20,
    default_user_routes=default_user_routes,
    output=output,
    temp_directory="/tmp/PSF/",
    silent_mode=False,
    backup_enable=True,
    flush=flush,
    ldap_settings=ldap_settings,
    max_workers=4,
    JWT_expire_interval=86399,
    smtp_api_host="localhost",
    smtp_api_port=25
)
