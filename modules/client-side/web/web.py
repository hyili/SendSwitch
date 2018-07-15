#!/usr/bin/env python3

from flask import request

from flask import Flask, url_for, jsonify, request, render_template
from flask_socketio import SocketIO, emit

def ManagementUI(config):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.kwargs["web_secret_key"]
    framework_name = config.kwargs["framework_name"]
    socketio = SocketIO(app)

    web_host = config.kwargs["web_host"]
    web_port = config.kwargs["web_port"]
    processors = config.kwargs["processors"]
    output = config.kwargs["output"]

    # Background thread
    # https://github.com/miguelgrinberg/Flask-SocketIO/blob/master/example/app.py
    def background_thread():
        while True:
            # data
            data = "testing"

            # info
            info = list()

            # try to fetch all the output message
            while True:
                msg = output.recv()
                if msg is not None:
                    info.append(msg)
                else:
                    break

            socketio.emit("server_statistic", {
                "data": data,
                "info": info
            }, namespace="/monitor")

            socketio.sleep(1)

    # Pages
    @app.route("/", methods=["Get"])
    def api_root():
        json = { "hello": "world" }
        return jsonify(json), 200

    @app.route("/manage", methods=["Get"])
    def manage():
        return render_template("manage.html"), 200

    @app.route("/monitor")
    def monitor():
        return render_template("monitor.html"), 200

    @socketio.on("client_event", namespace="/monitor")
    def client_msg(msg):
        emit("server_response", {"data": msg["data"]}, namespace="/monitor")

    @socketio.on("connect_event", namespace="/monitor")
    def connected_msg(msg):
        emit("server_response", {"data": msg["data"]}, namespace="/monitor")

    socketio.start_background_task(target=background_thread)
    socketio.run(app=app, host=web_host, port=web_port)
