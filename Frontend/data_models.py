from flask_login import UserMixin


# User model
class User(UserMixin):
    def __init__(self, id, username, email, password, role="user"):
        self.id = id
        self.username = username
        self.email = email
        self.password = password
        self.role = role

# Device model
class Device():
    def __init__(self, id, hostname, shown_name, software_version):
        self.id = id
        self.hostname = hostname
        self.shown_name = shown_name
        self.software_version = software_version