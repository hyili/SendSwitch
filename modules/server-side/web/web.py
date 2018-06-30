#!/usr/bin/env python3

from flask import request

from flask import Flask, url_for, request, render_template, flash, redirect
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

import os
import threading

from auth import ldap

# TODO: permission check
def ManagementUI(config):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "secret!"
    socketio = SocketIO(app)

    # LoginManager
    login_manager = LoginManager()
    login_manager.login_view = "/"
    login_manager.login_message = "Unauthorized User"
    login_manager.login_message_category = "info"
    login_manager.session_protection = "strong"
    login_manager.init_app(app)

    # config variable
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

    # Flask-Login load user_profile from user_profile
    # TODO: hashed token
    @login_manager.user_loader
    def load_user(email):
        # Create user_profile if nothing found
        user_profile = registered_users.get(email)
        if not user_profile:
            user_profile = registered_users.add(email=email, timeout=timeout)

        return user_profile

    # Flask-Login load user_profile from request coming from flask app
    # TODO: hashed token
    @login_manager.request_loader
    def load_user_from_request(request):
        # url args
        email = request.args.get("email")

        # Create user_profile if nothing found
        user_profile = registered_users.get(email)
        if not user_profile:
            user_profile = registered_users.add(email=email, timeout=timeout)

        return user_profile

    # Login Pages
    @app.route("/", methods=["Get"])
    def api_root():
        return render_template("helloworld.html"), 200

    # Flask-Login handle login user action page
    @app.route("/login", methods=["Post"])
    def login():
        # fetch form variable
        email = request.form.get("email")
        passwd = request.form.get("passwd")
        remember = request.form.get("remember")
        (account, domain) = email.split("@")

        if domain == email_domain:
            if ldap.ldap_authenticate(account, passwd, ldap_settings):
                # Create user_profile if nothing found
                user_profile = registered_users.get(email)
                if not user_profile:
                    user_profile = registered_users.add(email=email, timeout=timeout)

                if remember:
                    login_user(user_profile, remember=True)
                else:
                    login_user(user_profile)

                next = request.args.get("next")
                return redirect(next or url_for("manage"))
            else:
                flash("Error! Recheck your email and password!")
        else:
            flash("Are you sure that domain ({0}) is correct?".format(domain))

        return render_template("helloworld.html"), 200

    # Flask-Login handle logout user action page
    @app.route("/logout", methods=["Get", "Post"])
    def logout():
        logout_user()
        flash("Logged out successfully!")

        return render_template("helloworld.html"), 200

    # Flask-Login login required page
    @app.route("/manage", methods=["Get"])
    @login_required
    def manage():
        # get user id from current_user
        (account, domain) = current_user.get_id().split("@")

        return render_template("manage.html",
            account=account, domain=domain, src_servers=registered_servers.getSourceList(),
            dst_servers=registered_servers.getDestList()), 200

    # APIs
    # TODO: install to rabbitmq?
    @app.route("/activate", methods=["Post"])
    @login_required
    def activate():
        try:
            if current_user.is_activate():
                return "Already activated."
            else:
                current_user.activate()
                return "OK"
        except Exception as e:
            return str(e)

    # TODO: deinstall from rabbitmq?
    @app.route("/deactivate", methods=["Post"])
    @login_required
    def deactivate():
        try:
            if current_user.is_activate():
                current_user.deactivate()
                return "OK"
            else:
                return "Already deactivated."
        except Exception as e:
            return str(e)

    # setup route for user
    @app.route("/route", methods=["Post"])
    @login_required
    def route():
        local = request.form.get("local")
        remote = request.form.get("remote")

        try:
            if registered_servers.get(local) and registered_servers.get(remote):
                if local not in current_user.settings:
                    current_user.settings[local] = remote
                elif current_user.settings[local] != remote:
                    current_user.settings[local] = remote
                else:
                    return "Unchanged"
            return "OK"
        except Exception as e:
            return str(e)

    @app.route("/show/registered_users", methods=["Post"])
    @login_required
    def show_registered_users():
        return str(registered_users.getList())

    @app.route("/show/route", methods=["Post"])
    @login_required
    def show_route():
        try:
            return str(current_user.settings)
        except Exception as e:
            return "Some error occurred"

    @app.route("/flush", methods=["Post"])
    @login_required
    def flush_queuing_mail():
        try:
            queuing_list = current_user.get_queuing_list()
            for corr_id in queuing_list:
                flush.send(corr_id)
            return "OK"
        except Exception as e:
            return "Something wrong"

    @app.route("/monitor")
    def monitor():
        return render_template("monitor.html")

    @socketio.on("client_event", namespace="/monitor")
    def client_msg(msg):
        emit("server_response", {"data": msg["data"]}, namespace="/monitor")

    @socketio.on("connect_event", namespace="/monitor")
    def connected_msg(msg):
        emit("server_response", {"data": msg["data"]}, namespace="/monitor")

    socketio.start_background_task(target=background_thread)
    socketio.run(app=app, host=web_host, port=web_port)
