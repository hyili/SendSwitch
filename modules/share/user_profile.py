#!/usr/bin/env python3

class User():
    def __init__(self, email, timeout=600, settings=dict()):
        self.email = email
        self.account, self.domain = email.split("@")
        self.timeout = timeout
        self.queuing_list = list()
        self.settings = settings

    def add_queuing(self, corr_id):
        if corr_id not in self.queuing_list:
            self.queuing_list.append(corr_id)
            return corr_id
        else:
            return None

    def remove_queuing(self, corr_id):
        try:
            self.queuing_list.remove(corr_id)
        except:
            pass

    def get_queuing_list(self):
        return self.queuing_list

class Users():
    def __init__(self, settings=None):
        self.registered_user_profile = dict()
        self.default_user_settings = settings

    def add(self, email=None, timeout=600, user=None):
        if user:
            self.registered_user_profile[user.email] = user
        elif email:
            user = User(email, timeout)
            self.registered_user_profile[email] = user

    def get(self, email):
        try:
            return self.registered_user_profile[email]
        except:
            return None

    def getDefault(self):
        return self.default_user_settings

    def delete(self, email=None):
        if self.get(email):
            self.registered_user_profile.pop(email)

    def getList(self):
        return list(self.registered_user_profile.keys())
