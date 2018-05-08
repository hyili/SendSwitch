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
    timeout = config.kwargs["timeout"]
    output = config.kwargs["output"]

    # Background thread
    # https://github.com/miguelgrinberg/Flask-SocketIO/blob/master/example/app.py
    def background_thread():
        while True:
            server = registered_servers.get("Message-Queue-node")
            data = server.statistic
            log = list()

            while len(server.log) > 0:
                log.append(server.log.pop(0))

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
    def management_page():
        # fetch form variable
        email = request.form["email"]
        passwd = request.form["passwd"]
        (account, domain) = email.split("@")

        if domain == email_domain:
            if auth.ldap_authenticate(account, passwd):
                return render_template("manage.html",
                    account=account, domain=domain), 200
            else:
                return "Error!"
        else:
            return "Are you sure that domain ({0}) is correct?".format(domain)

    # APIs
    # TODO: install to rabbitmq?
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

    # for manual test
    @app.route("/add/<email>", methods=["Get"])
    def Get_add_user(email):
        if not registered_users.get(email):
            registered_users.add(email=email, timeout=timeout)
        return ""

    # TODO: deinstall from rabbitmq?
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
        return str(registered_users.getAll())

    @app.route("/monitor")
    def monitor():
        return render_template("monitor.html")

    @socketio.on("client_event", namespace="/monitor")
    def client_msg(msg):
        emit("server_response", {"data": msg["data"]}, namespace="/monitor")

    @socketio.on("connect_event", namespace="/monitor")
    def connected_msg(msg):
        emit("server_response", {"data": msg["data"]}, namespace="/monitor")

    # TODO: session SSO
    socketio.start_background_task(target=background_thread)
    socketio.run(app=app, host="0.0.0.0", port=60666)
