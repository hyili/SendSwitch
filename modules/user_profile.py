#!/usr/bin/env python3

class User():
    def __init__(self, email, setting=None):
        self.email = email
        self.account, self.domain = email.split("@")
        self.setting = setting


class Users():
    def __init__(self):
        self.registered_user_profile = dict()

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
