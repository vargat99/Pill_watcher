from flask_login import UserMixin


# Picture data model
class Picture():
    def __init__(self, name, device_id, encoder_position, timestamp):
        self.name = name
        self.device_id = device_id
        self.encoder_position = encoder_position
        self.timestamp = timestamp

# Device model
class Device():
    def __init__(self, id, hostname, shown_name, software_version, update_avaiable=False):
        self.id = id
        self.hostname = hostname
        self.shown_name = shown_name
        self.software_version = software_version
        self.update_avaiable = bool(int(update_avaiable))

# Settings model
class Settings():
    def __init__(self, id, device_id, morning_time="6:00:00", noon_time="11:00:00", evening_time="15:00:00", picture_delay_secs=60, use_flash=0):
        self.id = id
        self.device_id = device_id
        self.morning_time = str(morning_time).split(":")[0]
        self.noon_time = str(noon_time).split(":")[0]
        self.evening_time = str(evening_time).split(":")[0]
        self.picture_delay_secs = int(picture_delay_secs)
        self.use_flash = bool(int(use_flash))

# Update model
class Update():
    def __init__(self, id, host, path, version):
        self.id = id
        self.host = host
        self.path = path
        self.version = version