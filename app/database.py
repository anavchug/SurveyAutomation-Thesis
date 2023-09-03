import mysql.connector
from config import DATABASE_CONFIG

def get_database_connection():
    mydb = mysql.connector.connect(**DATABASE_CONFIG)
    return mydb