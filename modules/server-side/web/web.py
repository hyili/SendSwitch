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
    registered_servers = config.kwargs["registered_servers"]
    registered_users = config.kwargs["registered_users"]
    registered_server_routes = config.kwargs["registered_server_routes"]
    registered_user_routes = config.kwargs["registered_user_routes"]
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
            data = 0

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
        try:
            logout_user()
        except Exception as e:
            print(e)

        flash("Logged out successfully!")

        return render_template("helloworld.html"), 200

    # Flask-Login login required page
    @app.route("/manage", methods=["Get"])
    @login_required
    def manage():
        # get user "email" not "id" from current_user
        (account, domain) = current_user.get_id().split("@")
        _user_routes = registered_user_routes.getUserRoutes(current_user.id)
        user_routes = dict()
        if _user_routes:
            for route in _user_routes:
                user_routes[route.src.sid] = route

        _server_routes = registered_server_routes.getServerRoutes()
        server_routes = dict()
        if _server_routes:
            for route in _server_routes:
                server_routes[route.src.sid] = route

        servers = registered_servers.getList()
        src_servers = registered_servers.getSourceList()
        dst_servers = registered_servers.getDestList()

        return render_template("manage.html", user=current_user, user_routes=user_routes,
            servers=servers, server_routes=server_routes,
            src_servers=src_servers, dst_servers=dst_servers,
            account=account, domain=domain), 200

    # APIs
    # TODO: install to rabbitmq?
    @app.route("/service/activate", methods=["Post"])
    @login_required
    def activate_service():
        try:
            if current_user.serviceStatus():
                return "Already activated."
            else:
                if registered_users.activateService(current_user.id):
                    return "OK"
                else:
                    return "Failed"
        except Exception as e:
            return str(e)

    # TODO: deinstall from rabbitmq?
    @app.route("/service/deactivate", methods=["Post"])
    @login_required
    def deactivate_service():
        try:
            if current_user.serviceStatus():
                if registered_users.deactivateService(current_user.id):
                    return "OK"
                else:
                    return "Failed"
            else:
                return "Already deactivated."
        except Exception as e:
            return str(e)

    @app.route("/route/activate", methods=["Post"])
    @login_required
    def activate_route():
        try:
            if current_user.routeStatus():
                return "Already activated."
            else:
                if registered_users.activateRoute(current_user.id):
                    return "OK"
                else:
                    return "Failed"
        except Exception as e:
            return str(e)

    # TODO: add loop_check()
    @app.route("/route/deactivate", methods=["Post"])
    @login_required
    def deactivate_route():
        try:
            if current_user.routeStatus():
                if registered_users.deactivateRoute(current_user.id):
                    return "OK"
                else:
                    return "Failed"
            else:
                return "Already deactivated."
        except Exception as e:
            return str(e)

    # setup route for user
    @app.route("/route", methods=["Post"])
    @login_required
    def route():
        local_sid = request.form.get("local_sid")
        remote_sid = request.form.get("remote_sid")

        local = registered_servers.get(local_sid)
        remote = registered_servers.get(remote_sid)

        try:
            if local and remote:
                route = registered_user_routes.add(current_user.id, local.id, remote.id)
                if route:
                    return "OK"

                route = registered_user_routes.update(current_user.id, local.id, remote.id)
                if route:
                    return "OK"

            return "Unchanged"
        except Exception as e:
            return str(e)

    # TODO
    @app.route("/show/registered_users", methods=["Post"])
    @login_required
    def show_registered_users():
        email_list = registered_users.getEmailList()

        return str(email_list)

    # TODO
    @app.route("/show/route", methods=["Post"])
    @login_required
    def show_route():
        try:
            routes = registered_user_routes.getUserRoutes(current_user.id)
            if routes:
                ret = [(route.src.sid, route.dest.sid) for route in routes]
            else:
                ret = []

            return str(ret)
        except Exception as e:
            print(e)
            return "Something wrong"

    # TODO
    @app.route("/flush", methods=["Post"])
    @login_required
    def flush_queuing_mail():
        try:
            return "Wait for implement"
        except Exception as e:
            return "Something wrong"

    # Error Handler
    def error_page(subject, content):
        return "{0} {1}".format(subject, content)

    @app.errorhandler(Exception)
    def error_handler(error):
        return error_page("Error", "Something went wrong."), 500

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
