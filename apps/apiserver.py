#!/usr/bin/env python3

import flask

import json
import datetime

from flask import Flask, url_for
from flask import request
from flask import render_template

routing_key = ""
app = Flask(__name__)

@app.route("/", methods=["Get"])
def api_root():
    return render_template("helloworld.html"), 200

@app.route("/routingkey", methods=["Get", "Post"])
def exec():
    global routing_key

    dt = datetime.datetime.now()
    if request.method == "GET":
        data = json.dumps({
            "routing_key": routing_key,
            "datetime": str(dt)
        })
        return data, 200
    if request.method == "POST":
        data = request.get_json()

        if data is not None and "routing_key" in data:
            routing_key = data["routing_key"]
            ret = json.dumps({
                "status": "OK",
                "datetime": str(dt)
            })
            return ret, 200

    ret = json.dumps({
        "status": "Not OK",
        "datetime": str(dt)
    })

    return ret, 400

app.run(host="{localhost}", port="60666")
