from flask import Flask, render_template, request, redirect, session, flash
from mysqlconnection import connectToMySQL
import re
import base64
import os
#from datetime import datetime
from flask_bcrypt import Bcrypt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from yubico_client.py3 import b
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$') 
DATABASE = 'dojo_messages'
app = Flask(__name__)
app.secret_key = "Blahzay Blahzay"
bcrypt = Bcrypt(app)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/register', methods=['POST'])
def on_register():
    is_valid = True
    if len(request.form['fname']) < 2:
        is_valid = False
        flash("Please enter a first name of at least 2 characters")
    if len(request.form['lname']) < 2:
        is_valid = False
        flash("Please enter a last name of at least 2 characters")
    if len(request.form['email']) < 1:
        is_valid = False
        flash("Email cannot be blank", 'email')
    elif not EMAIL_REGEX.match(request.form['email']):
        is_valid = False
        flash("Invalid email address!", 'email')
    else:
        db = connectToMySQL(DATABASE)
        data = {
            "em": request.form['email']
        }
        result = db.query_db("SELECT * FROM users WHERE email = %(em)s",data)
        if len(result) > 0:
            flash("This email address is already registered.")
            is_valid = False
    if len(request.form['pass']) < 8:
        is_valid = False
        flash("Please enter a password of at least 8 characters")
    if request.form['pass'] != request.form['cpass']:
        is_valid = False
        flash("Passwords do not match")
    if is_valid:
        # include some logic to validate user input before adding them to the database!
        # create the hash
        pw_hash = bcrypt.generate_password_hash(request.form['pass'])  
        # print(pw_hash)  
        # prints something like b'$2b$12$sqjyok5RQccl9S6eFLhEPuaRaJCcH3Esl2RWLm/cimMIEnhnLb7iC'
        # be sure you set up your database so it can store password hashes this long (63 characters)
        email_provided = request.form['email'] # This is input in the form of a string
        email = email_provided.encode() # Convert to type bytes
        salt = b(os.urandom(30)) # CHANGE THIS - recommend using a key from os.urandom(16), must be of type bytes
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        ukey = base64.urlsafe_b64encode(kdf.derive(email))
        print(ukey)
        mysql = connectToMySQL(DATABASE)
        query = "INSERT INTO users (first_name, last_name, email, password, created_at, updated_at) VALUES (%(fn)s, %(ln)s, %(em)s, %(pw)s, NOW(), NOW());"
        data = {
            "fn": request.form["fname"],
            "ln": request.form["lname"],
            "em": request.form["email"],
            "pw": pw_hash
        }
        session['user_id'] = mysql.query_db(query, data)
        # add user to database
        # display success message
        # flash("User successfully added")
        mysql = connectToMySQL(DATABASE)
        query = "INSERT INTO dojo_messages.keys (user_id, user_key) VALUES (%(u_id)s, %(key)s);"
        data = {
            "u_id": session['user_id'],
            "key": ukey
        }
        mysql.query_db(query, data)
        return redirect('/dashboard')
    return redirect('/')

@app.route("/login", methods=["POST"])
def on_login():
    is_valid = True

    if len(request.form['email']) < 1:
        is_valid = False
        flash("Email cannot be blank")
    elif not EMAIL_REGEX.match(request.form['email']):    # test whether a field matches the pattern
        is_valid = False
        flash("Invalid email address!", 'email')
    
    if is_valid:
        mysql = connectToMySQL(DATABASE)
        query = "SELECT user_id, email, password FROM users WHERE email = %(em)s"
        data = {
            "em": request.form['email']
        }
        user_data = mysql.query_db(query, data)

        if user_data:
            user = user_data[0]

            if bcrypt.check_password_hash(user_data[0]['password'], request.form['pass']):
                session['user_id'] = user['user_id']
            # verify password
            # print(user_data)
                return redirect("/dashboard")
            else:
                flash("Email/Password combo is invalid")
                return redirect("/")
        else:
            flash("Please register first")
            return redirect("/")
    else:
        return redirect("/")

@app.route('/logout')
def on_logout():
    session.clear()
    return redirect("/")

@app.route('/dashboard')
def on_messages_dashboard():
    if 'user_id' not in session:
        return redirect('/')
    mysql = connectToMySQL(DATABASE)
    query = "SELECT first_name, last_name FROM users WHERE user_id = %(u_id)s"
    data = {
        'u_id': session['user_id']
    }
    user_data = mysql.query_db(query, data)
    if user_data:
        user_data = user_data[0]
    
    mysql = connectToMySQL(DATABASE)
    query = "SELECT *, COUNT(message_like_id) AS likes FROM messages JOIN users ON messages.author_id = users.user_id LEFT JOIN user_likes ON messages.message_id = user_likes.message_like_id GROUP BY messages.message_id"
    messages = mysql.query_db(query, data)

    # return render_template("thoughts.html", user_data=user_data, messages=messages, liked_messages=liked_messages)

    return render_template("dashboard.html", user_data=user_data, messages=messages)

if __name__ == "__main__":
    app.run(debug=True)