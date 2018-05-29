#!/usr/bin/env python3

from flask import request

from flask import Flask, url_for
from flask import request
from flask import render_template
from flask_socketio import SocketIO, emit

def ManagementUI():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "secret!"
    socketio = SocketIO(app)

    # Pages
    @app.route("/", methods=["Get"])
    def api_root():
        return render_template("helloworld.html"), 200


    # TODO: session SSO
    socketio.run(app=app, host="0.0.0.0", port=61666)
