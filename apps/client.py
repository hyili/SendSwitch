#!/usr/bin/env python3

# TODO: Here is to solve security issue
# that RabbitMQ reveals in public network may cause problems

import sys

sys.path.append("../modules/client-side")
from controller import Client_Controller
import web

sys.path.append("../config")
import client_config

# Config setup
config = client_config.config
silent_mode = config.kwargs["silent_mode"]

# Controller setup
Controller = Client_Controller(config, silent_mode)

try:
    print(" [*] Waiting for messages. To exit press CTRL+C")

    Controller.start()
    web.ManagementUI(config)

    print(" [*] Quit.")
    Controller.stop()
except KeyboardInterrupt:
    print(" [*] Signal Catched. Quit.")
    Controller.stop()
except Exception as e:
    print(" [*] Something wrong happened. {0}".format(e))
    Controller.stop()
