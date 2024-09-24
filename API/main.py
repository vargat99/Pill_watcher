from flask import Flask, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import os
import db
import my_secrets
import data_models


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db_connection = db.DBConnection(my_secrets.db_config)

# Ensure the upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check API key
    try:
        api_key = request.headers.get('X-API-Key')
        if api_key != my_secrets.API_KEY:
            print("Unauthorized, bad API key")
            return jsonify({"error": "Unauthorized"}), 401
    except:
        print("Unauthorized, failed API key check")
        return jsonify({"error": "Unauthorized"}), 401

    # Check if the post request has the file part
    if 'file' not in request.files:
        print("No file part")
        return "No file part", 400

    file = request.files['file']
    # If user does not select file, browser also submits an empty part without filename
    if file.filename == '':
        print("No selected file")
        return "No selected file", 400

    if file and allowed_file(file.filename):
        try:
            picture_name = file.filename.replace(":", "")
            encoder_position = int(request.headers.get('Encoder-Position'))
            if not encoder_position:
                encoder_position = 10000
            timestamp = request.headers.get('X-Timestamp')
            hostname = request.headers.get('Hostname')
            device_id = db_connection.get_device_id_by_hostname(hostname)
            print(picture_name, encoder_position, timestamp, hostname)
            if device_id == None:
                print("Device not found")
                return "Device not found", 400
            picture = data_models.Picture(picture_name, device_id, encoder_position, timestamp)
            filename = secure_filename(file.filename)
            filename = filename.replace(":", "")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            print("presavepicturedata")

            db_connection.save_picture_data(picture)

            print(f"File {filename} uploaded successfully")
            return f"File {filename} uploaded successfully", 200
        except:
            print("File upload failed")
            return "File upload failed", 400

    print("File type not allowed")
    return "File type not allowed", 400


@app.route('/get_data/<string:device_name>', methods=['GET'])
def get_device_data(device_name):
    data = db_connection.get_last_picture_data(device_name)
    return jsonify(success=True, timestamp=data.timestamp, encoder_position=data.encoder_position, picture_name=data.name)

@app.route('/get_data_multiple/<string:device_name>', methods=['GET'])
def get_device_data_multiple(device_name):
    pictures = db_connection.get_multiple_picture_data(device_name, 5)
    response = {
        'success': True,
        'data': [
            {
                'picture_name': pictures[0].name,
                'timestamp': pictures[0].timestamp,
                'encoder_position': pictures[0].encoder_position,
            },
            {
                'picture_name': pictures[1].name,
                'timestamp': pictures[1].timestamp,
                'encoder_position': pictures[1].encoder_position,
            },
            {
                'picture_name': pictures[2].name,
                'timestamp': pictures[2].timestamp,
                'encoder_position': pictures[2].encoder_position,
            },
            {
                'picture_name': pictures[3].name,
                'timestamp': pictures[3].timestamp,
                'encoder_position': pictures[3].encoder_position,
            },
            {
                'picture_name': pictures[4].name,
                'timestamp': pictures[4].timestamp,
                'encoder_position': pictures[4].encoder_position,
            },
        ]
    }
    return jsonify(response)

@app.route('/register_device/<string:device_name>', methods=['POST'])
def register_device(device_name):
    try:
        id = -1
        hostname = request.headers.get('Hostname')
        shown_name = hostname
        software_version = request.headers.get('Software-Verison')
        device = data_models.Device(id, hostname, shown_name, software_version)
        print(device.hostname, device.shown_name, device.software_version)
        try:
            db_connection.register_device(device)
            return "Registering device successful", 201
        except:
            return "Registering device failed", 400
    except:
        return "Adding device failed", 400

@app.route('/get_settings', methods=['GET'])
def get_settings():
    try:
        hostname = request.headers.get('Hostname')
    except:
        return "Failed to get hostname", 400


    try:
        # Get device id
        device_id = db_connection.get_device_id_by_hostname(hostname)
        
        # Get settings
        settings = db_connection.get_settings_by_device_id(device_id)
        if settings:
            return jsonify(morning_time=settings.morning_time, noon_time=settings.noon_time, evening_time=settings.evening_time, picture_delay=settings.picture_delay_secs, use_flash=settings.use_flash), 200
        else:
            return "No settings found", 204
    except:
        return "Failed to get settings", 400

@app.route('/update_settings', methods=['POST'])
def update_settings():
    try:
        hostname = request.headers.get('Hostname')
    except:
        return "Failed to get hostname", 400


    try:
        # Get device id
        device_id = db_connection.get_device_id_by_hostname(hostname)
        
        # Get settings data
        settings_data = request.json
        id = -1
        morning_time = settings_data["morning_time"]
        noon_time = settings_data["noon_time"]
        evening_time = settings_data["evening_time"]
        picture_delay_secs = settings_data["picture_delay"]
        use_flash = settings_data["use_flash"]
        settings = data_models.Settings(id, device_id, morning_time, noon_time, evening_time, picture_delay_secs, use_flash)
        
        db_connection.add_settings(settings)
        
        return "Settings updated", 200
    except:
        return "Failed to get settings", 400


@app.route('/check_update', methods=['GET'])
def check_for_update():
    try:
        hostname = request.headers.get('Hostname')
    except:
        return "Failed to get hostname", 400
    print(hostname)

    # Get device id
    device_id = db_connection.get_device_id_by_hostname(hostname)
    print(device_id)
    try:
        device = db_connection.get_device_by_id(device_id)
        if device.update_avaiable:
            update_data = db_connection.get_update_data()

            #Check if the version is newer:
            if update_data.version > device.software_version:
                db_connection.set_update_avaiable_to_false(device_id)

                return jsonify(host=update_data.host, path=update_data.path), 200

        return "No update avaiable", 204

    except:
        return "Failed to get updates", 400


@app.route("/")
def hello_world():
    """Example Hello World route."""
    name = os.environ.get("NAME", "World")
    return f"Hello {name}!"



if __name__ == '__main__':
    app.secret_key = 'supersecretkey'
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
