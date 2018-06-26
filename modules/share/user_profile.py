#!/usr/bin/env python3

class User():
    def __init__(self, email, timeout=600, settings=dict()):
        self.email = email
        self.account, self.domain = email.split("@")
        self.timeout = timeout
        self.queuing_list = list()
        self.settings = settings

        # disable routing service by default
        self.enable_service = False

        # Flask-Login some attributes
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def activate(self):
        self.enable_service = True

    def deactivate(self):
        self.enable_service = False

    def is_activate(self):
        return self.enable_service

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

    # Flask-Login get_id method
    # return current user's id
    def get_id(self):
        return self.email

class Users():
    def __init__(self, settings=None):
        self.registered_user_profile = dict()
        self.default_user_settings = settings

    def add(self, email=None, timeout=600):
        if isinstance(email, str):
            user = self.get(email)
            if not user:
                user = User(email, timeout, dict(self.default_user_settings))
                self.registered_user_profile[email] = user

            return user

        return None

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
