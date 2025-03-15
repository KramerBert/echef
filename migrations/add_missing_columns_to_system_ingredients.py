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

def add_missing_columns():
    """Add missing columns to system_ingredients table if they don't exist"""
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database")
        return False
        
    cursor = connection.cursor()
    missing_columns_added = 0
    try:
        # Check if omschrijving column exists
        cursor.execute("SHOW COLUMNS FROM system_ingredients LIKE 'omschrijving'")
        if not cursor.fetchone():
            print("Adding 'omschrijving' column to system_ingredients table...")
            cursor.execute("""
                ALTER TABLE system_ingredients
                ADD COLUMN omschrijving TEXT NULL AFTER prijs_per_eenheid
            """)
            missing_columns_added += 1
            print("Column 'omschrijving' added successfully")
            
        # Check if allergenen column exists
        cursor.execute("SHOW COLUMNS FROM system_ingredients LIKE 'allergenen'")
        if not cursor.fetchone():
            print("Adding 'allergenen' column to system_ingredients table...")
            cursor.execute("""
                ALTER TABLE system_ingredients
                ADD COLUMN allergenen VARCHAR(255) NULL AFTER omschrijving
            """)
            missing_columns_added += 1
            print("Column 'allergenen' added successfully")
            
        # Check if voorraad column exists
        cursor.execute("SHOW COLUMNS FROM system_ingredients LIKE 'voorraad'")
        if not cursor.fetchone():
            print("Adding 'voorraad' column to system_ingredients table...")
            cursor.execute("""
                ALTER TABLE system_ingredients
                ADD COLUMN voorraad DECIMAL(10,2) DEFAULT 0 AFTER allergenen
            """)
            missing_columns_added += 1
            print("Column 'voorraad' added successfully")
            
        connection.commit()
        
        if missing_columns_added > 0:
            print(f"Added {missing_columns_added} missing column(s) to system_ingredients table")
        else:
            print("No missing columns to add. All required columns already exist.")
            
        return True
    except Error as e:
        print(f"Error adding missing columns: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    print("Running migration to add missing columns to system_ingredients table...")
    success = add_missing_columns()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
