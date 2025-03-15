import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Create a connection to the database"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT")
        )
        if connection.is_connected():
            print("Connected to MySQL database")
            return connection
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

def remove_voorraad_column():
    """Remove voorraad column from system_ingredients table if it exists"""
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database")
        return False
        
    cursor = connection.cursor()
    try:
        # Check if voorraad column exists
        cursor.execute("SHOW COLUMNS FROM system_ingredients LIKE 'voorraad'")
        if cursor.fetchone():
            print("Column 'voorraad' exists, removing it...")
            cursor.execute("""
                ALTER TABLE system_ingredients
                DROP COLUMN voorraad
            """)
            connection.commit()
            print("Column 'voorraad' removed successfully")
            return True
        else:
            print("Column 'voorraad' does not exist, no action needed")
            return True
    except Error as e:
        print(f"Error removing voorraad column: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    print("Running migration to remove voorraad column from system_ingredients table...")
    success = remove_voorraad_column()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
