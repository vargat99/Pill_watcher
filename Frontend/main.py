from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_from_directory
import requests
import os
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from email_validator import validate_email, EmailNotValidError
import db
from datetime import date, datetime, timedelta
import my_secrets


app = Flask(__name__)

db_connection = db.DBConnection(config=my_secrets.db_config, logger=app.logger)

app.config['SECRET_KEY'] = my_secrets.secret_key
app.config['EXTERNAL_SERVICE_URL'] = my_secrets.external_service_url

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    try:
        user = db_connection.get_user_by_id(user_id)
        return user
    except Exception as e:
        app.logger.error(f"Error happened while loading user: {e}")
        return None

# Registration form
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = db_connection.get_user_by_username(username.data)
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')

    def validate_email(self, email):
        user = db_connection.get_user_by_email(email.data)
        if user:
            raise ValidationError('Email already registered. Please choose a different one.')

# Login form
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Device form
class DeviceForm(FlaskForm):
    device_name = StringField('Device Name', validators=[DataRequired(), Length(min=1, max=50)])
    submit = SubmitField('Add Device')

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            devices = db_connection.get_all_devices()
        else:
            devices = db_connection.get_all_device_for_user(current_user.id)
        return render_template('index.html', devices=devices)
    else:
        return render_template('index.html', devices=None)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            db_connection.create_user(form.username.data, form.email.data, hashed_password, datetime.now())
            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            app.logger.error(f"Error during registration: {e}")
            flash('There was an issue creating your account. Please try again later.', 'danger')
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = db_connection.get_user_by_email(form.email.data)
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('index'))
            flash('Login unsuccessful. Please check email and password.', 'danger')
        except Exception as e:
            app.logger.error(f"Error during login: {e}")
            flash('There was an issue logging you in. Please try again later.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/add_device', methods=['GET', 'POST'])
@login_required
def add_device():
    form = DeviceForm()
    if form.validate_on_submit():
        try:
            device_id = db_connection.get_device_id_by_hostname(form.device_name.data)
            if device_id:
                db_connection.create_connection(current_user.id, device_id)
                flash('Device added successfully!', 'success')
            else:
                flash('There was an issue finding your device. Please try again later.', 'danger')
            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f"Error adding device: {e}")
            flash('There was an issue adding your device. Please try again later.', 'danger')
    return render_template('add_device.html', form=form)

@app.route('/device/<int:device_id>')
@login_required
def device_details(device_id):
    try:
        device = db_connection.get_device_by_id(device_id)
        if not device:
            flash('Device not found or not authorized to view this device.', 'danger')
            return redirect(url_for('index'))

        if current_user.role == "admin":
            return render_template('device_details.html', device=device)

        devices = db_connection.get_all_device_for_user(current_user.id)
        device_ids = [device.id for device in devices]

        if device_id not in device_ids:
            flash('You are not authorized to view this device.', 'danger')
            return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error fetching device details: {e}")
        flash('There was an issue fetching the device details. Please try again later.', 'danger')
        return redirect(url_for('index'))
    return render_template('device_details.html', device=device)

@app.route('/get_data/<string:device_name>', methods=['GET'])
@login_required  # Ensure the user is logged in to access this endpoint
def get_device_data(device_name):
    try:
        external_service_url = app.config['EXTERNAL_SERVICE_URL']
        response = requests.get(f'{external_service_url}/get_data_multiple/{device_name}')
        if response.status_code == 200:
            return response.json()
            return jsonify(success=True, timestamp=data['timestamp'], encoder_position=data['encoder_position'], picture_name=data['picture_name'])
        else:
            app.logger.error(f"Error fetching data from external service: {response.status_code}")
            return jsonify(success=False)
    except Exception as e:
        app.logger.error(f"Error fetching data: {e}")
        return jsonify(success=False)

    example_response = {
        'success': True,
        'data': [
            {
                'picture_name': 'Spencer047DCC-2024-07-27T221350Z.jpg',
                'timestamp': '2024-07-27 22:13:50',
                'encoder_position': 3967,
            },
            {
                'picture_name': 'Spencer047DCC-2024-07-27T221340Z.jpg',
                'timestamp': '2024-07-27 22:13:40',
                'encoder_position': 3756,
            },
            {
                'picture_name': 'Spencer047DCC-2024-07-27T221330Z.jpg',
                'timestamp': '2024-07-27 22:13:30',
                'encoder_position': 3249,
            },
            {
                'picture_name': 'Spencer047DCC-2024-07-27T221323Z.jpg',
                'timestamp': '2024-07-27 22:13:23',
                'encoder_position': 3038,
            },
            {
                'picture_name': 'Spencer047DCC-2024-07-27T220536Z.jpg',
                'timestamp': '2024-07-27 22:05:36',
                'encoder_position': 3937,
            },
        ]
    }
    return jsonify(example_response)

# Serve files from the ../uploads directory
@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    uploads_dir = os.path.join(os.path.dirname(app.instance_path), 'uploads')
    app.logger.debug(f"Uploads dir: {uploads_dir}")
    filename = filename.replace(":", "")
    return send_from_directory(uploads_dir, filename)

@app.route('/get_device_settings/<string:device_name>', methods=['GET'])
@login_required
def get_device_settings(device_name):
    try:
        external_service_url = app.config['EXTERNAL_SERVICE_URL']
        response = requests.get(f'{external_service_url}/get_settings', headers={"Hostname": device_name})
        if response.status_code == 200:
            data = response.json()
            return jsonify(success=True, morning_time=data['morning_time'], noon_time=data['noon_time'],
                           evening_time=data['evening_time'], use_flash=data['use_flash'], picture_delay=data['picture_delay'])
        else:
            app.logger.error(f"Error fetching settings from external service: {response.status_code}")
            return jsonify(success=False)
    except Exception as e:
        app.logger.error(f"Error fetching settings: {e}")
        return jsonify(success=False)

@app.route('/update_device_settings/<string:device_name>', methods=['POST'])
@login_required
def update_device_settings(device_name):
    try:
        settings_data = request.json
        external_service_url = app.config['EXTERNAL_SERVICE_URL']
        response = requests.post(f'{external_service_url}/update_settings', json={**settings_data}, headers={'Hostname': device_name})
        if response.status_code == 200:
            return jsonify(success=True)
        else:
            app.logger.error(f"Error updating settings to external service: {response.status_code}")
            return jsonify(success=False)
    except Exception as e:
        app.logger.error(f"Error updating settings: {e}")
        return jsonify(success=False)

@app.route('/update_name/<device_name>', methods=['POST'])
@login_required
def update_name(device_name):
    new_name = request.json.get('new_name')
    if not new_name:
        return jsonify({'success': False, 'error': 'New name is required'})

    try:
        # Get device id
        device_id = db_connection.get_device_id_by_hostname(device_name)
        if device_id:
            db_connection.update_shown_name(device_id, new_name)
            return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f'Error updating device name: {e}')
        return jsonify({'success': False, 'error': 'An error occurred while updating the device name'})


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))