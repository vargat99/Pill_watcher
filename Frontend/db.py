import mysql.connector
from mysql.connector import errorcode
from datetime import date, datetime, timedelta
import my_secrets
import data_models



class DBConnection():
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.cnx = mysql.connector.connect(**self.config)
        self.DB_NAME = "Spencer2"
        try:
            cursor = self.cnx.cursor()
            cursor.execute("USE {}".format(self.DB_NAME))
        except mysql.connector.Error as err:
            self.logger.info("Database {} does not exists.".format(self.DB_NAME))
        finally:
            cursor.close()

    def __del__(self):
        self.cnx.close()

    def execute_command(self, command):
        pass

    def create_tables(self, tables):
        cursor = self.cnx.cursor()
        for table_name in tables:
            table_description = tables[table_name]
            try:
                self.logger.info("Creating table {}: ".format(table_name), end='')
                cursor.execute(table_description)
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                    self.logger.info("already exists.")
                else:
                    self.logger.error(err.msg)
            else:
                self.logger.info("OK")

        cursor.close()
        # Make sure data is committed to the database
        self.cnx.commit()

    def save_picture_data(self, picture):
        try:
            picture_name = picture.name
            device_id = picture.device_id
            encoder_position = picture.encoder_position
            timestamp = datetime.strptime(picture.timestamp, "%Y-%m-%dT%H:%M:%SZ")
            
            self.logger.debug(picture_name, device_id, encoder_position, timestamp)

            add_picture = f"INSERT INTO pictures (picture_name, device_id, encoder_position, timestamp) VALUES ('{picture_name}', '{device_id}', '{encoder_position}', '{timestamp}')"

            # Insert new picture
            cursor = self.cnx.cursor()
            self.logger.debug("Create cursor successful")
            cursor.execute(add_picture)
            self.logger.debug("Execute successful")
            pic_no = cursor.lastrowid
            self.logger.debug(pic_no)
        except Exception as e:
            self.logger.error(f"Error: {e}")
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

    def get_device_by_id(self, device_id):
        cursor = self.cnx.cursor()
        try:
            cursor.execute("SELECT * FROM devices WHERE id = %s", (device_id,))
            device = cursor.fetchone()
            if device:
                device = data_models.Device(device[0], device[1], device[2], device[3])
            else:
                device = None
        except Exception as e:
            self.logger.error(f"Error fetching device details: {e}")
            raise(f"Error fetching device details: {e}")
        finally:
            cursor.close()
        
        return device

    def get_all_devices(self):
        cursor = self.cnx.cursor()
        devices = []
        
        try:
            cursor.execute("SELECT * FROM devices")
            devices_data = cursor.fetchall()
            for device_data in devices_data:
                device = data_models.Device(device_data[0], device_data[1], device_data[2], device_data[3])
                devices.append(device)
        except Exception as e:
            self.logger.error(f"Error fetching device details: {e}")
            raise(f"Error fetching device details: {e}")
        finally:
            cursor.close()
        
        return devices

    def get_last_picture_data(self, hostname):
        device_id = self.get_device_id_by_hostname(hostname)
        if device_id:
            cursor = self.cnx.cursor()
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
            self.logger.error(f"Failed to execute command, reason: {e}")

        try:
            cursor.close()
        except Exception as e:
            self.logger.error(f"Failed to close cursor, reason: {e}")

        # Make sure data is committed to the database
        self.cnx.commit()

        self.logger.info("Commit successful")

    def get_user_by_id(self, user_id):      
        cursor = self.cnx.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                user_id = user_data[0]
                username = user_data[1]
                email = user_data[2]
                password = user_data[3]
                role = user_data[5]
                self.logger.debug(f"User data: {user_data}")
                return data_models.User(user_id, username, email, password, role)
        except Exception as e:
            self.logger.error(f"Error loading user: {e}")
            raise Exception(e)
        finally:
            cursor.close()

        return None

    def get_user_by_username(self, username):
        try:
            cursor = self.cnx.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user_data = cursor.fetchone()
            if user_data:
                user_id = user_data[0]
                username = user_data[1]
                email = user_data[2]
                password = user_data[3]
                role = user_data[5]
                self.logger.debug(f"User data: {user_data}")
                return data_models.User(user_id, username, email, password, role)
        except Exception as e:
            self.logger.error(f"There was an issue accessing the database. Please try again later. Error validating username: {e}")
            raise Exception(e)
        finally:
            cursor.close()

        return None

    def get_user_by_email(self, email):
        cursor = self.cnx.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user_data = cursor.fetchone()
            if user_data:
                user_id = user_data[0]
                username = user_data[1]
                email = user_data[2]
                password = user_data[3]
                role = user_data[5]
                self.logger.debug(f"User data: {user_data}")
                return data_models.User(user_id, username, email, password, role)
        except Exception as e:
            self.logger.error(f"There was an issue accessing the database. Please try again later. Error validating username: {e}")
            raise Exception(e)
        finally:
            cursor.close()

        return None

    def get_all_device_for_user(self, user_id):
        try:
            cursor = self.cnx.cursor()
            # Get all devices associated with user
            cursor.execute("SELECT * FROM connections WHERE user_id = %s", (user_id,))
            devices = cursor.fetchall()
            devices = str(tuple([device[2] for device in devices]))
            if devices[-2] == ",":
                devices = devices.replace(",", "")

            # Get all devices with the ids
            cursor.execute(f"SELECT * FROM devices WHERE id IN {devices}")
            devices = cursor.fetchall()
            devices = [data_models.Device(device[0], device[1], device[2], device[3]) for device in devices]      
        except Exception as e:
            self.logger.error(f"Error fetching devices: {e}")
            devices = []
        finally:
            cursor.close()

        return devices

    def create_user(self, username, email, hashed_password, created_at):
        try:
            cursor = self.cnx.cursor()
            cursor.execute("INSERT INTO users (username, email, password, created_at) VALUES (%s, %s, %s, %s)", (username, email, hashed_password, created_at))
            self.cnx.commit()
        except Exception as e:
            self.logger.error(f"Error during registration: {e}")
            raise Exception(f'There was an issue creating your account: {e}')
        finally:
            cursor.close()

    def create_connection(self, user_id, device_id):
        try:
            cursor = self.cnx.cursor()
            cursor.execute("INSERT INTO connections (user_id, device_id) VALUES (%s, %s)", (user_id, device_id))
            self.cnx.commit()
        except Exception as e:
            self.logger.error(f"Error during adding device: {e}")
            raise Exception('There was an issue adding the device: {e}')
        finally:
            cursor.close()

    def update_shown_name(self, device_id, shown_name):
        try:
            cursor = self.cnx.cursor()
            cursor.execute(f"UPDATE devices SET shown_name = '{shown_name}' WHERE id = {device_id}")
            self.cnx.commit()
        except Exception as e:
            self.logger.error(f"Error during updating device name: {e}")
            raise Exception('There was an issue updating device name: {e}')
        finally:
            cursor.close()


if __name__ == '__main__':
    db = DBConnection(my_secrets.db_config)
    print(db.get_last_picture_data("Spencer047DCC"))