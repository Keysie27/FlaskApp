import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
import pathlib
from pip._vendor import cachecontrol
from google.oauth2 import id_token
import google.auth.transport.requests
from google_auth_oauthlib.flow import Flow
from flask import Flask, session, abort, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
import requests
import os
    
app = Flask(__name__)
app.secret_key = "Flaskweb" 

GOOGLE_CLIENT_ID = "125381192790-hvai1237mcmegg5gcttu6p0a41868oul.apps.googleusercontent.com"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file = client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)

# Conección Mysql 
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'flaskapp'
mysql = MySQL(app)

# Ajustes
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = "mysecretkey"

def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()
    return wrapper

@app.route('/login')
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    flow.fetch_token(authorization_response = "https://" + request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token = credentials._id_token,
        request = token_request,
        audience = GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    return redirect("/protected_area")

@app.route('/inicio')
def inicio():
    return "<h1>Inicio</h1><a href='/login'><button>Login</button></a>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/inicio")

@app.route('/protected_area')
@login_is_required
def protected_area():
    return "<h1>Area Protegida</h1><a href='/logout'><button>Logout</button></a>"

@app.route('/')
def home():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM contacts')
    data = cursor.fetchall()
    return render_template("index.html", title = "Home", contactos = data)

@app.route('/add', methods=['GET', 'POST'])
def add_contact():
    if request.method == 'POST':
        fullname = request.form['fullname']
        phone = request.form['phone']
        email = request.form['email']
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO contacts (fullname, phone, email) VALUES (%s, %s, %s)', (fullname, phone, email))
        mysql.connection.commit()
        flash("Contacto agregado.")
        return redirect(url_for('home'))
    else:
        return render_template("add.html", title = "Add")    

@app.route('/get/<id>')
def get_contact(id):
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM contacts WHERE id = {0}'.format(id))
    data = cursor.fetchall()
    return render_template("edit.html", title = "Edit", contactos = data[0]) 

@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit_contact(id):
    if request.method == 'POST':
        fullname = request.form['fullname']
        phone = request.form['phone']
        email = request.form['email']
        cursor = mysql.connection.cursor()
        cursor.execute('UPDATE contacts SET fullname = "{0}", phone = "{1}", email = "{2}" WHERE id = {3}'.format(fullname, phone, email, id))
        mysql.connection.commit()
        flash("Contacto editado.")
        return redirect(url_for('home'))

@app.route('/delete/<string:id>')
def delete_contact(id):
    cursor = mysql.connection.cursor()
    cursor.execute('DELETE FROM contacts WHERE id = {0}'.format(id))
    mysql.connection.commit()
    flash("Contacto Removido.")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)