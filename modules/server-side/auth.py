#!/usr/bin/env python3

# http://ldap3.readthedocs.io/tutorial_intro.html#logging-into-the-server
from ldap3 import Server, Connection, ALL, NTLM

def ldap_authenticate(account, passwd, ldap_settings=None):
    try:
        ldap_server = ldap_settings["ldap_server"]
        use_ssl = ldap_settings["use_ssl"]
        dn = ldap_settings["user_dn"].format(account)
    except Exception as e:
        print(e)
        return False

    try:
        server = Server(ldap_server, use_ssl=False, get_info=ALL)
        connection = Connection(server, dn, passwd, auto_bind=True)
    except Exception as e:
        print(e)
        return False

    return True
