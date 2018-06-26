#!/usr/bin/env python3

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP

class ServerController(Controller):
    def __init__(self, handler, loop=None, hostname=None, port=8025, decode_data=False):
        self.decode_data = decode_data

        super().__init__(handler=handler, loop=loop, hostname=hostname, port=port)

    def factory(self):
        return SMTP(self.handler, enable_SMTPUTF8=self.enable_SMTPUTF8, decode_data=self.decode_data)
