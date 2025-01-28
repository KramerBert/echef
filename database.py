import mysql.connector
from mysql.connector import Error, pooling
from contextlib import contextmanager
from functools import lru_cache
import time

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
    """
    Creates a new database connection using the configuration
    """
    try:
        conn = mysql.connector.connect(**dbconfig)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error connecting to the database: {e}")
        return None

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
