#!/usr/bin/env python3

from flask import request

from flask import Flask, url_for
from flask import request
from flask import render_template
import auth

def ManagementUI(config):
    app = Flask(__name__)
    registered_users = config.kwargs["registered_users"]

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

        if domain == "{localhost}":
            if auth.ldap_authenticate(account, passwd):
                return render_template("manage.html",
                    account=account, domain=domain), 200
            else:
                return "Error!"
        else:
            return "Are you sure that domain ({0}) is correct?".format(domain)

    # APIs
    # TODO: add button
    @app.route("/add", methods=["Post"])
    def add_user():
        try:
            account = request.form["account"]
            domain = request.form["domain"]
            email = "{0}@{1}".format(account, domain)
            if not registered_users.get(email):
                registered_users.add(email)
                return "OK"
            else:
                return "already activated"
        except Exception as e:
            return str(e)

    # for manual test
    @app.route("/add/<email>", methods=["Get"])
    def Get_add_user(email):
        if not registered_users.get(email):
            registered_users.add(account=email)
        return ""

    # TODO: add button
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

    # TODO: add button
    @app.route("/show", methods=["Post"])
    def show_user():
        return str(registered_users.getAll())

    # TODO: session SSO
    app.run(host="{localhost}", port=60666)
