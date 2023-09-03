from flask import Flask
# from .config import SECRET_KEY, SESSION_TYPE, DATABASE_CONFIG
import config
import mysql.connector

def create_app():
    # Create the Flask application instance
    app = Flask(__name__, static_folder="static")

    # Configure the Flask app
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['SESSION_TYPE'] = config.SESSION_TYPE

    # Connect to MySQL database
    mydb = mysql.connector.connect(**config.DATABASE_CONFIG)
    app.config['MYSQL_DATABASE'] = mydb

    # Import and register the blueprints
    from views.auth import auth_bp
    from views.company import company_bp
    from views.data_analysis import data_analysis_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(data_analysis_bp)
    app.register_blueprint(company_bp)

    return app
