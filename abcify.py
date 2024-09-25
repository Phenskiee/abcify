import bcrypt
import os
import io
import base64
import tensorflow as tf
import numpy as np
import joblib
from tensorflow.keras.preprocessing.image import img_to_array
from gtts import gTTS
from PIL import Image
from flask import Flask, render_template, redirect, url_for, flash, session, jsonify, request
from flask_wtf import  FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, ValidationError
from flask_mysqldb import MySQL
from tensorflow.keras.applications import VGG16
from tensorflow.keras.applications.vgg16 import preprocess_input

abcify = Flask(__name__, template_folder = "HTML", static_folder = "Assets")

# DATABASE CONFIGURATION
abcify.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
abcify.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
abcify.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'ABCiFY')
abcify.secret_key = os.getenv('SECRET_KEY', 'ABCIFYY')

mysql = MySQL(abcify)

def title_case(s):
    return ' '.join(word.capitalize() for word in s.split())

abcify.jinja_env.filters['title_case'] = title_case

# FOR REGISTRATION FORM
class RegisterForm(FlaskForm):
    first_name = StringField(render_kw={'placeholder': 'First name'}, validators=[DataRequired()])
    last_name = StringField(render_kw={'placeholder': 'Last name'}, validators=[DataRequired()])
    nickname = StringField(render_kw={'placeholder': 'Nickname'}, validators=[DataRequired()])
    password = PasswordField(render_kw={'placeholder': 'Password'}, validators=[DataRequired()])
    submit = SubmitField("Register")
    
    # USER VALIDATION IN REGISTER
    def validate_nickname(self, field):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE nickname=%s", (field.data,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            raise ValidationError('Nickname is Already Taken')

# FOR LOGIN FORM
class LoginForm(FlaskForm):
    nickname = StringField("Nickname", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

# PASWORD RESET REQUEST FORM
class PasswordResetRequestForm(FlaskForm):
    nickname = StringField("Nickname", validators=[DataRequired()])
    submit = SubmitField("Request password reset")

# PASSWORD RESET FORM
class PasswordResetForm(FlaskForm):
    password = PasswordField("New password",validators=[DataRequired()])
    submit = SubmitField("Reset password")

# Load the model and class names
alphabet_model = tf.keras.models.load_model('saved_models/alphabets.keras')
class_names_encoder = joblib.load('saved_models/class_names.joblib')

class_names = class_names_encoder.classes_

base_model = VGG16(weights='imagenet', include_top=False, input_shape=(256, 256, 3))

# ROUTES FOR ALL PANEL
@abcify.route('/')
def welcome():
    return render_template('index.html')

#################### REGISTER PANEL #####################
@abcify.route('/register.html', methods = ['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        first_name = form.first_name.data
        last_name = form.last_name.data
        nickname = form.nickname.data
        password = form.password.data

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        # STORE DATA INTO DATABSE
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users (first_name, last_name, nickname, password) VALUES(%s, %s, %s, %s)",
                        (first_name, last_name, nickname, hashed_password.decode('utf-8')))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('login'))
    
    return render_template('/register.html', form=form)

##################### LOGIN PANEL ######################
@abcify.route('/login.html', methods = ['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        nickname = form.nickname.data
        password = form.password.data

        # SELECT USER FROM DATABASE
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE nickname = %s", (nickname,))
        user = cursor.fetchone()
        cursor.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[4].encode('utf-8')):
            session['user_id'] = user[0]
            return redirect(url_for('home'))
        else:
            flash('Check your nickname and password', 'error')
            return redirect(url_for('login'))
    
    return render_template('/login.html', form=form)

################## REQUEST TO RESET PASSWORD PANEL ###################
@abcify.route('/request_password_reset.html', methods=['GET', 'POST'])
def request_password_reset():
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        nickname = form.nickname.data

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE nickname=%s", (nickname,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            # Store the nickname in the session to use later
            session['reset_nickname'] = nickname
            return redirect(url_for('reset_password'))

        flash('Nickname not found.', 'error')
    
    return render_template('/request_password_reset.html', form=form)

################### RESET PASSWORD PANEL ####################
@abcify.route('/reset_password.html', methods=['GET', 'POST'])
def reset_password():
    form = PasswordResetForm()
    if form.validate_on_submit():
        new_password = form.password.data
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

        nickname = session.pop('reset_nickname', None)
        if nickname:
            cursor = mysql.connection.cursor()
            cursor.execute("UPDATE users SET password=%s WHERE nickname=%s", (hashed_password.decode('utf-8'), nickname))
            mysql.connection.commit()
            cursor.close()

            flash('Your password has been updated.', 'success')

            return redirect(url_for('login'))

        flash('Reset session expired or invalid.', 'error')
    
    return render_template('/reset_password.html', form=form)

##################### HOME PANEL ######################
@abcify.route('/home.html')
def home():
    if 'user_id' in session:
        user_id = session['user_id']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            return render_template('/home.html', user=user)

    return redirect(url_for('login'))

##################### IMAGE PROCESSING FOR SCAN OBJECT ######################
def preprocess_image(image_data):
    # Decode base64 image
    image_data = image_data.split(",")[1] if "," in image_data else image_data
    image_bytes = io.BytesIO(base64.b64decode(image_data))
    image = Image.open(image_bytes).convert('RGB')
    
    # Resize image to (256, 256) if required by the model
    if image.size != (256, 256):
        image = image.resize((256, 256))

    # Convert image to numpy array and normalize
    image_array = np.array(image) / 255.0  # Normalize to [0, 1]
    
    # Add batch dimension
    return np.expand_dims(image_array, axis=0)

##################### SCAN OBJECT PANEL ######################
@abcify.route('/scan_object.html', methods=['GET', 'POST'])
def scan_object():
    return render_template('/scan_object.html')

@abcify.route('/predict', methods=["POST"])
def predict():
    if 'base64Image' in request.form:
        image_data = request.form['base64Image']
    elif 'image' in request.files:
        image_file = request.files['image']
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
    else:
        return jsonify({'error': 'No image data provided'}), 400

    try:
        preprocessed_image = preprocess_image(image_data)
        predictions = alphabet_model.predict(preprocessed_image)
        predicted_index = np.argmax(predictions, axis=-1)[0]
        predicted_class = class_names.inverse_transform([predicted_index])[0]
        
        # Return the name of the predicted class
        return jsonify({'prediction': predicted_class})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#################### LOGOUT PANEL #####################
@abcify.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    abcify.run(debug=True)