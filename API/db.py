import mysql.connector
from mysql.connector import errorcode
from datetime import date, datetime, timedelta
from tables import TABLES, DB_NAME
import my_secrets
import data_models



class DBConnection():
    def __init__(self, config):
        self.config = config
        self.cnx = mysql.connector.connect(**self.config)
        try:
            cursor = self.cnx.cursor()
            cursor.execute("USE {}".format(DB_NAME))
        except mysql.connector.Error as err:
            print("Database {} does not exists.".format(DB_NAME))
        finally:
            cursor.close()

    def __del__(self):
        self.cnx.close()

    def create_tables(self):
        cursor = self.cnx.cursor()
        for table_name in TABLES:
            table_description = TABLES[table_name]
            try:
                print("Creating table {}: ".format(table_name), end='')
                cursor.execute(table_description)
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                    print("already exists.")
                else:
                    print(err.msg)
            else:
                print("OK")

        # Make sure data is committed to the database
        self.cnx.commit()

    def save_picture_data(self, picture):
        try:
            picture_name = picture.name
            device_id = picture.device_id
            encoder_position = picture.encoder_position
            timestamp = datetime.strptime(picture.timestamp, "%Y-%m-%dT%H:%M:%SZ")
            
            print(picture_name, device_id, encoder_position, timestamp)

            add_picture = f"INSERT INTO pictures (picture_name, device_id, encoder_position, timestamp) VALUES ('{picture_name}', '{device_id}', '{encoder_position}', '{timestamp}')"

            # Insert new picture
            cursor = self.cnx.cursor()
            print("Create cursor successful")
            cursor.execute(add_picture)
            print("Execute successful")
            pic_no = cursor.lastrowid
            print(pic_no)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            cursor.close()

            # Make sure data is committed to the database
            self.cnx.commit()

    def get_device_id_by_hostname(self, hostname):
        cursor = self.cnx.cursor()
        cursor.execute("SELECT * FROM devices WHERE hostname = %s", (hostname,))
        device_data = cursor.fetchone() 
        cursor.close()
        
        if device_data:
            device_id = device_data[0]
            return device_id
        else:
            return None

    def get_last_picture_data(self, hostname):
        device_id = self.get_device_id_by_hostname(hostname)
        if device_id:
            cursor = self.cnx.cursor(buffered=True)
            cursor.execute(f"SELECT * FROM pictures WHERE device_id = {device_id} ORDER by `timestamp` DESC")
            picture_data = cursor.fetchone()
            cursor.close()
            if picture_data:
                name = picture_data[1]
                device_id = picture_data[2]
                encoder_position = picture_data[3]
                timestamp = picture_data[4]
                return data_models.Picture(name, device_id, encoder_position, timestamp)
        return None

    def get_multiple_picture_data(self, hostname, num_pictures):
        device_id = self.get_device_id_by_hostname(hostname)
        pictures = []
        if device_id:
            cursor = self.cnx.cursor(buffered=True)
            cursor.execute(f"SELECT * FROM pictures WHERE device_id = {device_id} ORDER by `timestamp` DESC")
            picture_datas = cursor.fetchmany(size=num_pictures)
            cursor.close()
            for picture_data in picture_datas:
                if picture_data:
                    name = picture_data[1]
                    device_id = picture_data[2]
                    encoder_position = picture_data[3]
                    timestamp = picture_data[4]
                    picture = data_models.Picture(name, device_id, encoder_position, timestamp)
                    pictures.append(picture)
            return pictures
        return None

    def register_device(self, device):
        hostname = device.hostname
        shown_name = device.shown_name
        software_version = device.software_version

        add_device = f"INSERT INTO devices (hostname, shown_name, software_version) VALUES ('{hostname}', '{shown_name}', '{software_version}')"

        # Insert new device
        cursor = self.cnx.cursor()
        try:
            cursor.execute(add_device)
        except Exception as e:
            print(f"Failed to execute command, reason: {e}")

        try:
            cursor.close()
            print("Close successful")
        except Exception as e:
            print(f"Failed to close cursor, reason: {e}")
            raise Exception(f"Failed to close cursor, reason: {e}")

        # Make sure data is committed to the database
        self.cnx.commit()

        print("commit successful")

    def get_device_by_id(self, device_id):
        cursor = self.cnx.cursor()
        try:
            cursor.execute("SELECT * FROM devices WHERE id = %s", (device_id,))
            device = cursor.fetchone()
            if device:
                device = data_models.Device(device[0], device[1], device[2], device[3], device[4])
            else:
                device = None
        except Exception as e:
            print(f"Error fetching device details: {e}")
            raise Exception(f"Error fetching device details: {e}")
        finally:
            cursor.close()
        
        return device

    def set_update_avaiable_to_false(self, device_id):
        cursor = self.cnx.cursor()
        try:
            cursor.execute("UPDATE devices SET update_avaiable=0 WHERE id = %s", (device_id,))
            device = cursor.fetchone()
            if device:
                device = data_models.Device(device[0], device[1], device[2], device[3], device[4])
            else:
                device = None
        except Exception as e:
            print(f"Error fetching device details: {e}")
            raise Exception(f"Error fetching device details: {e}")
        finally:
            cursor.close()

        # Make sure data is committed to the database
        self.cnx.commit()

    def get_settings_by_device_id(self, device_id):
        cursor = self.cnx.cursor(buffered=True)
        try:
            cursor.execute(f"SELECT * FROM settings WHERE device_id = {device_id} ORDER by `updated_at` DESC")
            settings = cursor.fetchone()
            if settings:
                settings = data_models.Settings(settings[0], settings[1], settings[2], settings[3], settings[4], settings[5], settings[6])
            else:
                settings = None
        except Exception as e:
            print(f"Error fetching settings: {e}")
            raise Exception(f"Error fetching settings: {e}")
        finally:
            cursor.close()
        
        return settings

    def add_settings(self, settings):
        cursor = self.cnx.cursor()
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            add_settings = f"INSERT INTO settings (device_id, morning_time, noon_time, night_time, picture_delay_secs, use_flash, updated_at) VALUES ('{settings.device_id}', '{settings.morning_time}:00:00', '{settings.noon_time}:00:00', '{settings.evening_time}:00:00', '{settings.picture_delay_secs}', '{int(settings.use_flash)}', '{timestamp}')"

            cursor.execute(add_settings)
        except Exception as e:
            print(f"Error adding settings: {e}")
            raise Exception(f"Error adding settings: {e}")
        finally:
            cursor.close()

        # Make sure data is committed to the database
        self.cnx.commit()

    def get_update_data(self):
        cursor = self.cnx.cursor(buffered=True)
        try:
            cursor.execute(f"SELECT * FROM updates ORDER by `id` DESC")
            updates = cursor.fetchone()
            if updates:
                update = data_models.Update(updates[0], updates[1], updates[2], updates[3])
            else:
                update = None
        except Exception as e:
            print(f"Error fetching updates: {e}")
            raise Exception(f"Error fetching updates: {e}")
        finally:
            cursor.close()
        
        return update


if __name__ == '__main__':
    db = DBConnection(my_secrets.db_config)
    device_id = db.get_device_id_by_hostname("Spencer047DCC")
    # device = db.get_device_by_id(device_id)
    # print(device.update_avaiable)
    # db.set_update_avaiable_to_false(device_id)

    settings = db.get_settings_by_device_id(device_id)
    print(settings.morning_time)