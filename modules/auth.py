#!/usr/bin/env python3

# http://ldap3.readthedocs.io/tutorial_intro.html#logging-into-the-server
from ldap3 import Server, Connection, ALL, NTLM

def ldap_authenticate(account, passwd):
    dn = "uid={0}".format(account)
    ldap_server = "localhost"

    try:
        server = Server(ldap_server, use_ssl=False, get_info=ALL)
        connection = Connection(server, dn, passwd, auto_bind=True)
    except Exception as e:
        print(e)
        return False

    return True
