#!/usr/bin/env python3

from config_loader import Config
from shared_queue import SharedQueue
import user_profile
import server_profile
import server_route

# DB setup
db_host = "localhost"
db_port = 3306
db_name = "db_name"
db_user = "db_user"
db_passwd = "db_passwd"

# Server setup
servers = server_profile.Servers(db_host=db_host, db_port=db_port, db_name=db_name,
    db_user=db_user, db_passwd=db_passwd)

# Postfix
Pi = servers.get("Postfix-incoming-node")
if not Pi:
    Pi = servers.add(sid="Postfix-incoming-node", hostname="localhost", port=8025, dest=False)
Po = servers.get("Postfix-outgoing-node")
if not Po:
    Po = servers.add(sid="Postfix-outgoing-node", hostname="localhost", port=10025, source=False)

# Amavisd-new
Ai = servers.get("Amavisd-new-incoming-node")
if not Ai:
    Ai = servers.add(sid="Amavisd-new-incoming-node", hostname="localhost", port=8024, dest=False)
Ao = servers.get("Amavisd-new-outgoing-node")
if not Ao:
    Ao = servers.add(sid="Amavisd-new-outgoing-node", hostname="localhost", port=10024, source=False)

# Message Queue node
MQ = servers.get("Message-Queue-node")
if not MQ:
    MQ = servers.add(sid="Message-Queue-node", hostname="localhost", port=8026)

# TODO: prevent loop
# Server next hop setup
default_routes = {
    "Postfix-incoming-node": "Message-Queue-node",
    "Message-Queue-node": "Postfix-outgoing-node",
    "Amavisd-new-incoming-node": "Postfix-outgoing-node"
}

# TODO: route settings
# User setup with default route settings
users = user_profile.Users(db_host=db_host, db_port=db_port, db_name=db_name,
    db_user=db_user, db_passwd=db_passwd)

# TODO: route
# Route setup
routes = server_route.Routes(db_host=db_host, db_port=db_port, db_name=db_name,
    db_user=db_user, db_passwd=db_passwd)

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
config = Config(registered_servers=servers,
    registered_users=users,
    registered_routes=routes,
    email_domain="hyili.idv.tw",
    host_domain="hyili.idv.tw",
    MQ_host="localhost",
    MQ_port=5672,
    web_host="localhost",
    web_port=60666,
    timeout=60,
    retry_interval=20,
    default_routes=default_routes,
    output=output,
    temp_directory="/tmp/PSF/",
    silent_mode=False,
    backup_enable=True,
    flush=flush,
    ldap_settings=ldap_settings,
    max_workers=4
)
