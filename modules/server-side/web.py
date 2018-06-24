#!/usr/bin/env python3

from flask import request

from flask import Flask, url_for
from flask import request
from flask import render_template
from flask_socketio import SocketIO, emit

import os
import threading

import auth
import install
import per_user_install

def ManagementUI(config):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "secret!"
    socketio = SocketIO(app)

    registered_users = config.kwargs["registered_users"]
    registered_servers = config.kwargs["registered_servers"]
    email_domain = config.kwargs["email_domain"]
    host_domain = config.kwargs["host_domain"]
    web_host = config.kwargs["web_host"]
    web_port = config.kwargs["web_port"]
    timeout = config.kwargs["timeout"]
    output = config.kwargs["output"]
    flush = config.kwargs["flush"]
    ldap_settings = config.kwargs["ldap_settings"]

    # Background thread
    # https://github.com/miguelgrinberg/Flask-SocketIO/blob/master/example/app.py
    def background_thread():
        while True:
            # email statistic
            server = registered_servers.get("Message-Queue-node")
            data = server.statistic

            # logging
            log = list()

            # try to fetch all the output message
            while True:
                msg = output.recv()
                if msg is not None:
                    log.append(msg)
                else:
                    break

            socketio.emit("server_statistic", {
                "data": data,
                "log": log
            }, namespace="/monitor")

            socketio.sleep(1)

    # Pages
    @app.route("/", methods=["Get"])
    def api_root():
        return render_template("helloworld.html"), 200

    @app.route("/manage", methods=["Post"])
    def manage():
        # fetch form variable
        email = request.form["email"]
        passwd = request.form["passwd"]
        (account, domain) = email.split("@")

        if domain == email_domain:
            if auth.ldap_authenticate(account, passwd, ldap_settings):
                return render_template("manage.html",
                    account=account, domain=domain, src_servers=registered_servers.getSourceList(),
                    dst_servers=registered_servers.getDestList()), 200
            else:
                return "Error!"
        else:
            return "Are you sure that domain ({0}) is correct?".format(domain)

    # APIs
    # TODO: install to rabbitmq?
    # TODO: permission check
    @app.route("/add", methods=["Post"])
    def add_user():
        try:
            account = request.form["account"]
            domain = request.form["domain"]
            email = "{0}@{1}".format(account, domain)
            if not registered_users.get(email):
                registered_users.add(email=email, timeout=timeout)
                return "OK"
            else:
                return "already activated"
        except Exception as e:
            return str(e)

    # Only for manual test
    @app.route("/add/<email>", methods=["Get"])
    def Get_add_user(email):
        if not registered_users.get(email):
            registered_users.add(email=email, timeout=timeout)
        return ""

    # TODO: deinstall from rabbitmq?
    # TODO: permission check
    @app.route("/del", methods=["Post"])
    def del_user():
        try:
            account = request.form["account"]
            domain = request.form["domain"]
            email = "{0}@{1}".format(account, domain)
            if registered_users.get(email):
                registered_users.delete(email)
                return "OK"
            else:
                return "not activated yet"
        except Exception as e:
            return str(e)

    # TODO: setup route for user
    # TODO: permission check
    @app.route("/route", methods=["Post"])
    def route():
        account = request.form["account"]
        domain = request.form["domain"]
        email = "{0}@{1}".format(account, domain)
        local = request.form["local"]
        remote = request.form["remote"]

        user = registered_users.get(email)
        if user:
            try:
                if registered_servers.get(local) and registered_servers.get(remote):
                    if local not in user.settings:
                        user.settings[local] = remote
                    elif user.settings[local] != remote:
                        user.settings[local] = remote
                    else:
                        return "Unchanged"
                return "OK"
            except Exception as e:
                return "No such server node"
        else:
            return "Who are you"

    @app.route("/show", methods=["Post"])
    def show_user():
        return str(registered_users.getList())

    # TODO: permission check
    @app.route("/flush", methods=["Post"])
    def flush_queuing_mail():
        account = request.form["account"]
        domain = request.form["domain"]
        email = "{0}@{1}".format(account, domain)

        user = registered_users.get(email)
        if user:
            try:
                queuing_list = user.get_queuing_list()
                for corr_id in queuing_list:
                    flush.send(corr_id)
                return "OK"
            except Exception as e:
                return "Something wrong"
        else:
            return "Who are you"

    # TODO: permission check
    @app.route("/monitor")
    def monitor():
        return render_template("monitor.html")

    # TODO: permission check
    @socketio.on("client_event", namespace="/monitor")
    def client_msg(msg):
        emit("server_response", {"data": msg["data"]}, namespace="/monitor")

    # TODO: permission check
    @socketio.on("connect_event", namespace="/monitor")
    def connected_msg(msg):
        emit("server_response", {"data": msg["data"]}, namespace="/monitor")

    # TODO: session SSO
    socketio.start_background_task(target=background_thread)
    socketio.run(app=app, host=web_host, port=web_port)