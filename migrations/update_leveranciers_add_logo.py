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

def add_logo_path_column():
    """Add logo_path column to leveranciers table if it doesn't exist"""
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database")
        return False
        
    cursor = connection.cursor()
    try:
        # Check if the column already exists
        cursor.execute("SHOW COLUMNS FROM leveranciers LIKE 'logo_path'")
        if cursor.fetchone():
            print("Column logo_path already exists in leveranciers table")
            return True
            
        # Add the logo_path column
        cursor.execute("""
            ALTER TABLE leveranciers
            ADD COLUMN logo_path VARCHAR(255) NULL AFTER has_standard_list
        """)
        
        print("Column logo_path added successfully to leveranciers table")
        connection.commit()
        return True
    except Error as e:
        print(f"Error adding logo_path column: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    print("Running migration to add logo_path column to leveranciers table...")
    success = add_logo_path_column()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
