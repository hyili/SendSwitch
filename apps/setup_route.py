#!/usr/bin/env python3

import sys

sys.path.append("../modules/MessageQueue")
from install import install
from per_user_install import per_user_install

if __name__ == "__main__":
    try:
        args = sys.argv
        if len(args) == 3:
            username, domain = args[2].split("@")
            rabbitmq_host = args[1]

            install = install(host=rabbitmq_host, username=username, email_domain=domain)
            pisntall = per_user_install(host=rabbitmq_host, vhost=username)
        else:
            print("./setup_route.py {rabbitmq_host} {username}@{domain}")
    except KeyboardInterrupt:
        print(" [*] Signal Catched. Quit.")
