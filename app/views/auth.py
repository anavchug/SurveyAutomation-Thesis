from flask import Blueprint, render_template, redirect, request, url_for, session
from database import get_database_connection

auth_bp = Blueprint('auth', __name__)
mydb = get_database_connection()

@auth_bp.route('/', methods=['GET', 'POST'])
def index(): #login route
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username and password are valid in the database
        query = "SELECT * FROM Accounts WHERE username = %s AND password = %s"
        cursor = mydb.cursor()
        cursor.execute(query, (username, password))
        user = cursor.fetchone()

        if user:
            # Store the user's information in the session
            session['username'] = user[1]
            session['user_id'] = user[0]  # Store the user ID in the session
            return redirect('/dashboard')
        else:
            return 'Invalid username or password'

    return render_template("login.html")

@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username is already taken
        query = "SELECT * FROM Accounts WHERE username = %s"
        cursor = mydb.cursor()
        cursor.execute(query, (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            return 'Username already exists'
        else:
            # Insert the new user into the database
            query = "INSERT INTO Accounts (username, password) VALUES (%s, %s)"
            cursor.execute(query, (username, password))
            mydb.commit()

            # Store the user's information in the session
            session['username'] = username
            return redirect('/')

    return render_template("register.html")

@auth_bp.route('/dashboard')
def dashboard():
     # Check if the user is logged in by checking the session
    if 'username' in session:
        username = session['username']
        return render_template("CompanyDashboard.html", username = username)
    else:
        return redirect('/')
    pass

@auth_bp.route('/logout', methods=['POST'])
def logout():
    # Clear the session and redirect to the login page
    session.clear()
    return redirect('/')
    
