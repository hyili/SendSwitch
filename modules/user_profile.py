#!/usr/bin/env python3

class User():
    def __init__(self, email, settings=dict()):
        self.email = email
        self.account, self.domain = email.split("@")
        self.timeout = 600
        self.settings = settings


class Users():
    def __init__(self, settings=None):
        self.registered_user_profile = dict()
        self.default_user_settings = settings

    def add(self, email=None, user=None):
        if user:
            self.registered_user_profile[user.email] = user
        elif email:
            user = User(email)
            self.registered_user_profile[email] = user

    def get(self, email):
        try:
            return self.registered_user_profile[email]
        except:
            return None

    def delete(self, email=None):
        if self.get(email):
            self.registered_user_profile.pop(email)

    def getAll(self):
        return list(self.registered_user_profile.keys())
