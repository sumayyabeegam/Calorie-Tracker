import os
import shutil
from flask import Flask, render_template, request, g, session
from werkzeug.utils import secure_filename
import mysql.connector
from flask_caching import Cache
from PIL import Image
import numpy as np
from skimage import transform
import keras
from datetime import date

app = Flask(__name__)

UPLOAD_FOLDER = "static/output"

config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'calorie_tracker',
}

app.config['SECRET_KEY'] = 'sumu123'
cache = Cache(app, config={'CACHE_TYPE': 'redis',
              'CACHE_REDIS_URL': 'redis://localhost:6379/0'})

today = date.today()
current_date = today.strftime("%Y-%m-%d")

# mysql helper functions


def insert_record(query, data):
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    cursor.execute(query, data)

    cnx.commit()
    cursor.close()
    cnx.close()


def update_record(query, data):
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()

    cursor.execute(query, data)

    cnx.commit()
    cursor.close()
    cnx.close()


def select_records(query):
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()

    cursor.execute(query)

    rows = cursor.fetchall()

    cursor.close()
    cnx.close()
    return rows

# homepage routes


@app.route('/')
def index():

    return render_template('home/index.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':

        query = "select * from master where email='"+request.form['email']+"'"
        res = select_records(query)
        print(res)
        if res == []:
            query = "insert into user values (%s,%s,%s,%s,%s,%s,%s,%s)"
            data = (request.form['email'], request.form['fname'], request.form['lname'],  request.form['age'],
                    request.form['gender'], request.form['weight'], request.form['height'], request.form['factor'])
            insert_record(query, data)

            query = "insert into master values (%s,%s)"
            data = (request.form['email'], request.form['pass'])
            insert_record(query, data)
            return '''
                <script>
                alert('Registered successfully!');
                window.location.href = '/user/';
                </script>
                '''
        else:
            return '''
                <script>
                alert('Email already registered!');
                window.location.href = '/';
                </script>
                '''
    else:
        return render_template('home/register.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        query = "select * from master where email='"+request.form['email']+"'"
        res = select_records(query)
        print(res)
        if res != []:
            if res[0][1] == request.form['pass']:
                session['user_id'] = res[0][0]
                return '''
                <script>
                alert('Welcome Back!');
                window.location.href = '/user/';
                </script>
                '''
            else:
                return '''
                <script>
                alert('Invalid credential!');
                window.location.href = '/';
                </script>
                '''
        else:
            return '''
                <script>
                alert('Email not registered!');
                window.location.href = '/';
                </script>
                '''
    else:
        return render_template('home/login.html')


# userpage routes
@app.route('/user/', methods=["POST", "GET"])
def index2():
    if 'user_id' in session.keys():

        query = "select * from user where email='"+session['user_id']+"'"
        res = select_records(query)
        fname = res[0][1]
        lname = res[0][2]
        age = res[0][3]
        gender = res[0][4]
        weight = res[0][5]
        height = res[0][6]
        factor = res[0][7]
        g = 5 if gender == 'male' else -161
        rcalorie = calorie_cal(weight, height, age, g, factor)

        query = "select * from food where user='" + \
            session['user_id']+"' and cdate='"+current_date+"'"
        res2 = select_records(query)
        print(res2)
        ccalorie = 0
        for x in res2:
            ccalorie += x[4]
        if request.method == 'POST':
            calories = [311, 267, 240]
            qty = int(request.form['qty'])
            f = request.files['file']
            filename = secure_filename(f.filename)
            f.save(os.path.join(UPLOAD_FOLDER, filename))

            pt = os.path.join(os.getcwd(), UPLOAD_FOLDER, filename)

            file = filename

            model = keras.models.load_model("model")

            image = load(pt)
            pred = model.predict(image)
            print(pred)
            c = np.argmax(pred)
            print(pred, "\t", c)

            calo = (calories[c]/100)*qty
            query = "insert into food (user,food_class,qty,calorie) values (%s,%s,%s,%s)"

            data = (session['user_id'], int(c), qty, calo)
            insert_record(query, data)

            return render_template('user/index.html', fname=fname, lname=lname, age=age, gender=gender, weight=weight, height=height, factor=factor, res=c, file=file, rcalorie=rcalorie, ccalorie=ccalorie)
        else:
            return render_template('user/index.html', fname=fname, lname=lname, age=age, gender=gender, weight=weight, height=height, factor=factor, res=-1, file="", rcalorie=rcalorie, ccalorie=ccalorie)
    else:
        return render_template('home/index.html')


@ app.route('/user/profile', methods=["POST", "GET"])
def profile():
    if 'user_id' in session.keys():
        if request.method == 'POST':
            query = "update user set age=%s,weight=%s,height=%s,factor=%s where email=%s"
            data = (request.form['age'], request.form['weight'],
                    request.form['height'], request.form['factor'], session['user_id'])
            update_record(query, data)

            query = "select * from user where email='"+session['user_id']+"'"
            res = select_records(query)
            email = res[0][0]
            fname = res[0][1]
            lname = res[0][2]
            age = res[0][3]
            gender = res[0][4]
            weight = res[0][5]
            height = res[0][6]
            factor = res[0][7]
            return render_template('user/profile.html', email=email, fname=fname, lname=lname, age=age, gender=gender, weight=weight, height=height, factor=factor)
        else:
            query = "select * from user where email='"+session['user_id']+"'"
            res = select_records(query)
            email = res[0][0]
            fname = res[0][1]
            lname = res[0][2]
            age = res[0][3]
            gender = res[0][4]
            weight = res[0][5]
            height = res[0][6]
            factor = res[0][7]
            return render_template('user/profile.html', email=email, fname=fname, lname=lname, age=age, gender=gender, weight=weight, height=height, factor=factor)
    else:
        return render_template('home/index.html')


@ app.route('/user/analytics')
def analytics():
    return "null"


@ app.route('/user/logout')
def logout():
    if 'user_id' in session.keys():
        session.pop('user_id', None)
        return render_template('home/index.html')
    else:
        return render_template('home/index.html')


def load(filename):
    np_image = Image.open(filename)
    np_image = np.array(np_image).astype('float32')/255
    np_image = transform.resize(np_image, (224, 224, 3))
    np_image = np.expand_dims(np_image, axis=0)
    return np_image


def calorie_cal(W, H, A, G, F):
    calorie = (10*W + 6.25*H - 5*A + G)*F
    return np.round(calorie)
