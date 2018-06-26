#!/usr/bin/env python3

from config_loader import Config
from shared_queue import SharedQueue
import user_profile
import server_profile

# Server setup
servers = server_profile.Servers()
servers.add(id="Message-Queue-node", hostname="localhost", port=8025, dest=False)
servers.add(id="Amavisd-new-node", hostname="localhost", port=8026)
servers.add(id="Postfix", hostname="localhost", port=10026, source=False)
servers.add(id="Noop", hostname="localhost", port=10000, source=False)

# Check servers
for id in servers.getList():
    server = servers.get(id)
    print(" [*] Server Settings OK: id: \"{0}\", hostname: \"{1}\", port: {2}".
        format(server.id, server.hostname, server.port))

# Server next hop setup
default_user_settings = {
    "Message-Queue-node": "Postfix",
    "Amavisd-new-node": "Noop"
}

# Check settings are correct
for key in default_user_settings:
    if servers.get(key) is None:
        raise(Exception(" [*] default_user_settings: \"{0}\" not in servers".
            format(key)))
    if servers.get(default_user_settings[key]) is None:
        raise(Exception(" [*] default_user_settings: \"{0}\" not in servers".
            format(default_user_settings[key])))

    print(" [*] Route Settings OK: from: \"{0}\" to: \"{1}\"".
        format(key, default_user_settings[key]))

# User setup with default route settings
users = user_profile.Users(settings=default_user_settings)

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
    email_domain="hyili.idv.tw",
    host_domain="hyili.idv.tw",
    MQ_host="localhost",
    MQ_port=5672,
    web_host="localhost",
    web_port=60666,
    timeout=60,
    retry_interval=20,
    output=output,
    temp_directory="/tmp/PSF/",
    silent_mode=False,
    backup_enable=True,
    flush=flush,
    ldap_settings=ldap_settings,
    max_workers=4
)
