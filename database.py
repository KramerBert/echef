import os
import mysql.connector
from mysql.connector import Error, pooling
from contextlib import contextmanager
from functools import lru_cache
import time
from urllib.parse import urlparse

dbconfig = {
    "host": "localhost",
    "database": "echef",
    "user": "root",
    "password": ""
}

connection_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="echef_pool",
    pool_size=5,
    **dbconfig
)

def get_db_connection():
    """Creates a new database connection using environment variables"""
    try:
        # Check for JawsDB URL (Heroku)
        db_url = os.getenv("JAWSDB_URL")
        
        if db_url:  # Production/Heroku
            url = urlparse(db_url)
            config = {
                'host': url.hostname,
                'database': url.path[1:],
                'user': url.username,
                'password': url.password,
                'port': url.port
            }
        else:  # Local development
            config = {
                'host': os.getenv("DB_HOST"),
                'database': os.getenv("DB_NAME"),
                'user': os.getenv("DB_USER"),
                'password': os.getenv("DB_PASSWORD"),
                'port': os.getenv("DB_PORT")
            }
        
        conn = mysql.connector.connect(**config)
        if conn.is_connected():
            return conn
            
    except Error as e:
        raise Exception(f"Database connection failed: {str(e)}")

@contextmanager
def get_db_cursor(dictionary=True):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=dictionary)
        yield cursor
        conn.commit()
    except Error as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

# Cache voor vaak opgevraagde data
@lru_cache(maxsize=32)
def get_cached_ingredients(timestamp):
    """Cache ingrediënten voor 5 minuten"""
    with get_db_cursor() as cursor:
        cursor.execute(PREPARED_STATEMENTS['get_ingredienten'])
        return cursor.fetchall()

# Prepared statements voor vaak gebruikte queries
PREPARED_STATEMENTS = {
    'get_gerecht': "SELECT * FROM gerechten WHERE dish_id = %s",
    'get_ingredienten': "SELECT * FROM ingredienten",
    'get_gerecht_ingredienten': """
        SELECT gi.*, i.naam as ingredient_naam, i.eenheid, i.prijs_per_eenheid,
               (gi.hoeveelheid * i.prijs_per_eenheid) as prijs_totaal
        FROM gerecht_ingredient gi
        JOIN ingredienten i ON gi.ingredient_id = i.ingredient_id
        WHERE gi.gerecht_id = %s
    """,
    'update_gerecht': """
        UPDATE gerechten 
        SET naam = %s, beschrijving = %s, categorie = %s, bereidingswijze = %s
        WHERE dish_id = %s
    """,
    'add_ingredient': """
        INSERT INTO gerecht_ingredient (gerecht_id, ingredient_id, hoeveelheid)
        VALUES (%s, %s, %s)
    """
}

# Bulk operations toevoegen
BULK_STATEMENTS = {
    'add_ingredients_bulk': """
        INSERT INTO gerecht_ingredient (gerecht_id, ingredient_id, hoeveelheid)
        VALUES (%s, %s, %s)
    """,
    'update_ingredients_bulk': """
        UPDATE gerecht_ingredient 
        SET hoeveelheid = %s 
        WHERE gerecht_id = %s AND ingredient_id = %s
    """
}

def execute_bulk_operation(query, data_list):
    """Voer bulk operaties uit met error handling en rollback"""
    with get_db_cursor() as cursor:
        try:
            cursor.executemany(query, data_list)
            return True
        except Error as e:
            print(f"Bulk operation failed: {e}")
            raise
