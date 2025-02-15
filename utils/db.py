import os
import mysql.connector
from mysql.connector import Error
from urllib.parse import urlparse
from flask import current_app

def get_db_connection():
    """
    Creates a new database connection using the application config
    """
    try:
        db_url = os.getenv("JAWSDB_URL")
        if db_url:  # Heroku
            url = urlparse(db_url)
            DB_CONFIG = {
                'host': url.hostname,
                'database': url.path[1:],
                'user': url.username,
                'password': url.password,
                'port': url.port
            }
        else:  # Local development
            DB_CONFIG = {
                'host': os.getenv("DB_HOST"),
                'database': os.getenv("DB_NAME"),
                'user': os.getenv("DB_USER"),
                'password': os.getenv("DB_PASSWORD"),
                'port': os.getenv("DB_PORT")
            }

        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
        else:
            return None
    except Error as e:
        current_app.logger.error(f"Error connecting to the database: {e}")
        return None
