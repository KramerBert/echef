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

def add_allergenen_column():
    """Add allergenen column to system_ingredients table if it doesn't exist"""
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database")
        return False
        
    cursor = connection.cursor()
    try:
        # Check if allergenen column exists
        cursor.execute("SHOW COLUMNS FROM system_ingredients LIKE 'allergenen'")
        if not cursor.fetchone():
            print("Adding 'allergenen' column to system_ingredients table...")
            cursor.execute("""
                ALTER TABLE system_ingredients
                ADD COLUMN allergenen VARCHAR(255) NULL AFTER categorie
            """)
            connection.commit()
            print("Column 'allergenen' added successfully")
            return True
        else:
            print("Column 'allergenen' already exists")
            return True
    except Error as e:
        print(f"Error adding allergenen column: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    print("Running migration to add allergenen column to system_ingredients table...")
    success = add_allergenen_column()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
