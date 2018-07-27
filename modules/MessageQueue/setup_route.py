#!/usr/bin/env python3

import sys

from install import install
from per_user_install import per_user_install

def setup_route(username, domain, rabbitmq_host, rabbitmq_port):
    install(host=rabbitmq_host, port=rabbitmq_port, username=username, email_domain=domain)
    per_user_install(host=rabbitmq_host, port=rabbitmq_port, vhost=username, username=username, email_domain=domain)

if __name__ == "__main__":
    try:
        args = sys.argv
        if len(args) == 3:
            username, domain = args[2].split("@")
            rabbitmq_host, rabbitmq_port = args[1].split(":")

            setup_route(username, domain, rabbitmq_host, rabbitmq_port)
        else:
            print("./setup_route.py {rabbitmq_host}:{port} {username}@{domain}")
    except KeyboardInterrupt:
        print(" [*] Signal Catched. Quit.")
