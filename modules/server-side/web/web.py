#!/usr/bin/env python3

from flask import request

from flask import Flask, url_for, request, render_template, flash, redirect
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

import os
import jwt
import email
import datetime
import smtplib
import threading

from auth import ldap

# TODO: permission check
def ManagementUI(config):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.kwargs["web_secret_key"]
    framework_name = config.kwargs["framework_name"]
    socketio = SocketIO(app)

    # jwt variable
    HASH_algo = "HS256"

    # LoginManager
    login_manager = LoginManager()
    login_manager.login_view = "/"
    login_manager.login_message = "Unauthorized User"
    login_manager.login_message_category = "info"
    login_manager.session_protection = "strong"
    login_manager.init_app(app)

    # config variable
    logger = config.kwargs["logger"]
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
    JWT_expire_interval = config.kwargs["JWT_expire_interval"]
    smtp_api_host = config.kwargs["smtp_api_host"]
    smtp_api_port = config.kwargs["smtp_api_port"]

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

    def Debug(msg):
        logger.info(" [*] {0}".format(msg))

    # Flask-Login load user_profile from user_profile
    @login_manager.user_loader
    def load_user(email):
        # Create user_profile if nothing found
        user_profile = registered_users.get(email)
        if not user_profile:
            user_profile = registered_users.add(email=email, timeout=timeout)

        return user_profile

    # Flask-Login load user_profile from request coming from flask app
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
            Debug("Something wrong happened during logout(), reason: {0}.".format(e))
            return error_page("Error", "Something went wrong."), 500

        flash("Logged out successfully!")

        return render_template("helloworld.html"), 200

    # Manage Page
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

    # TODO: install to rabbitmq?
    @app.route("/service/activate", methods=["Post"])
    @login_required
    def activate_service():
        try:
            if current_user.serviceStatus():
                return "Already activated.", 200
            else:
                if registered_users.activateService(current_user.id):
                    return "OK", 200
                else:
                    return "Failed", 200
        except Exception as e:
            Debug("Something wrong happened during activate_service(), reason: {0}.".format(e))
            return error_page("Error", "Something went wrong."), 500

    # TODO: deinstall from rabbitmq?
    @app.route("/service/deactivate", methods=["Post"])
    @login_required
    def deactivate_service():
        try:
            if current_user.serviceStatus():
                if registered_users.deactivateService(current_user.id):
                    return "OK", 200
                else:
                    return "Failed", 200
            else:
                return "Already deactivated.", 200
        except Exception as e:
            Debug("Something wrong happened during deactivate_service(), reason: {0}.".format(e))
            return error_page("Error", "Something went wrong."), 500

    @app.route("/route/activate", methods=["Post"])
    @login_required
    def activate_route():
        try:
            if current_user.routeStatus():
                return "Already activated.", 200
            else:
                if registered_users.activateRoute(current_user.id):
                    return "OK", 200
                else:
                    return "Failed", 200
        except Exception as e:
            Debug("Something wrong happened during activate_route(), reason: {0}.".format(e))
            return error_page("Error", "Something went wrong."), 500

    @app.route("/route/deactivate", methods=["Post"])
    @login_required
    def deactivate_route():
        try:
            if current_user.routeStatus():
                if registered_users.deactivateRoute(current_user.id):
                    return "OK", 200
                else:
                    return "Failed", 200
            else:
                return "Already deactivated.", 200
        except Exception as e:
            Debug("Something wrong happened during deactivate_route(), reason: {0}.".format(e))
            return error_page("Error", "Something went wrong."), 500

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
                    return "OK", 200

                route = registered_user_routes.update(current_user.id, local.id, remote.id)
                if route:
                    return "OK", 200

            return "Unchanged", 200
        except Exception as e:
            Debug("Something wrong happened during route(), reason: {0}.".format(e))
            return error_page("Error", "Something went wrong."), 500

    @app.route("/show/registered_users", methods=["Post"])
    @login_required
    def show_registered_users():
        email_list = registered_users.getEmailList()
        ret = str(email_list)

        return ret, 200

    @app.route("/show/route", methods=["Post"])
    @login_required
    def show_route():
        try:
            routes = registered_user_routes.getUserRoutes(current_user.id)
            if routes:
                ret = str([(route.src.sid, route.dest.sid) for route in routes])
            else:
                ret = str([])

            return ret, 200
        except Exception as e:
            Debug("Something wrong happened during show_route(), reason: {0}.".format(e))
            return error_page("Error", "Something went wrong."), 500

    # TODO
    @app.route("/flush", methods=["Post"])
    @login_required
    def flush_queuing_mail():
        try:
            return "Wait for implementation", 200
        except Exception as e:
            Debug("Something wrong happened during flush_queuing_mail(), reason: {0}.".format(e))
            return error_page("Error", "Something went wrong."), 500

    # Error Handler
    def error_page(subject, content):
        return "{0} {1}".format(subject, content)

    @app.errorhandler(Exception)
    def error_handler(error):
        Debug("Something wrong happened during web(), reason: {0}.".format(error))
        return error_page("Error", "Something went wrong."), 500

    # Monitor Page
    @app.route("/monitor")
    def monitor():
        return render_template("monitor.html"), 200

    @socketio.on("client_event", namespace="/monitor")
    def client_msg(msg):
        emit("server_response", {"data": msg["data"]}, namespace="/monitor")

    @socketio.on("connect_event", namespace="/monitor")
    def connected_msg(msg):
        emit("server_response", {"data": msg["data"]}, namespace="/monitor")

    # SMTP API
    @app.route("/api_key", methods=["Get"])
    @login_required
    def api_key():
        try:
            current_time = datetime.datetime.utcnow()
            uid = current_user.id
            email = "{0}@{1}".format(current_user.account, current_user.domain)

            payload = {
                "iss": framework_name,
                "iat": current_time,
                "exp": current_time+datetime.timedelta(seconds=JWT_expire_interval),
                "data": {
                    "uid": uid,
                    "email": email,
                }
            }
            api_key = jwt.encode(payload, app.config["SECRET_KEY"], algorithm=HASH_algo)

            return api_key, 200
        except Exception as e:
            Debug("Something wrong happened during api_key(), reason: {0}.".format(e))
            return error_page("Error", "Something went wrong."), 500

    @app.route("/smtp", methods=["Post"])
    def smtp():
        try:
            # Request
            # {
            #   "data": {
            #     "api_key": "API_KEY",
            #     "mail_from": "user1@domain",
            #     "mail_to": ["user2@domain", "user3@domain"],
            #     "cc_to": ["user4@domain", "user5@domain"],
            #     "bcc_to": ["user6@domain", "user7@domain"],
            #     "subject": "SUBJECT",
            #     "content": "CONTENT"
            #   }
            # }
            # get dict from application/json content-type request
            content = request.json
            if not content:
                return "Please POST your data in json type.", 400

            try:
                api_key = content["data"]["api_key"]
                payload = jwt.decode(api_key, app.config["SECRET_KEY"], algorithms=[HASH_algo])

                # Check user data
                user = registered_users.get(payload["data"]["email"])
                if user.id != payload["data"]["uid"]:
                    return "Invalid api_key.", 403

                # Check expiration
                current = datetime.datetime.utcnow()
                expire = datetime.datetime.fromtimestamp(payload["exp"])
                if current > expire:
                    return "Expired api_key.", 403
            except Exception as e:
                print(e)
                return "Invalid api_key.", 403

            # Check if the incoming request is valid
            mail_to_upper_bound = 10
            mail_to_lower_bound = 1
            cc_to_upper_bound = 20
            bcc_to_upper_bound = 20
            try:
                # mail_from's address must be user's email address
                mail_from = content["data"]["mail_from"]
                if mail_from != payload["data"]["email"]:
                    return "Invalid mail_from address.", 403

                mail_to = content["data"]["mail_to"]
                if len(mail_to) > mail_to_upper_bound:
                    return "Maximum number of {0} addresses in mail_to exceeded.".format(mail_to_upper_bound), 400

                if len(mail_to) < mail_to_lower_bound:
                    return "There must be at least {0} address in mail_to.".format(mail_to_lower_bound), 400

                cc_to = content["data"]["cc_to"]
                if len(cc_to) > cc_to_upper_bound:
                    return "Maximum number of {0} addresses in cc_to exceeded.".format(cc_to_upper_bound), 400

                bcc_to = content["data"]["bcc_to"]
                if len(bcc_to) > bcc_to_upper_bound:
                    return "Maximum number of {0} addresses in bcc_to exceeded.".format(bcc_to_upper_bound), 400

                subject = content["data"]["subject"]
                content = content["data"]["content"]
            except:
                return "Some required keys are missing, please recheck.", 400

            ## Send Mail Here ##
            try:
                msg = email.message.EmailMessage()
                msg.set_content(content)
                msg["From"] = mail_from
                msg["To"] = mail_to
                if len(cc_to) > 0:
                    msg["Cc"] = cc_to
                msg["Subject"] = subject

                to_list = mail_to + cc_to + bcc_to

                s = smtplib.SMTP()
                s.connect(smtp_api_host, smtp_api_port)
                s.send_message(msg, to_addrs=to_list)
                s.quit()
            except Exception as e:
                Debug("Something wrong happened during smtp(), reason: {0}.".format(e))
                return error_page("Error", "Something went wrong."), 500

            return "OK, mail sent.", 200
        except Exception as e:
            Debug("Something wrong happened during smtp(), reason: {0}.".format(e))
            return error_page("Error", "Something went wrong."), 500

    socketio.start_background_task(target=background_thread)
    socketio.run(app=app, host=web_host, port=web_port)
