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

def create_system_ingredients_table():
    """Create the system_ingredients table if it doesn't exist"""
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database")
        return False
        
    cursor = connection.cursor()
    try:
        # Check if table already exists
        cursor.execute("SHOW TABLES LIKE 'system_ingredients'")
        if cursor.fetchone():
            print("Table system_ingredients already exists")
            return True
            
        # Create the system_ingredients table
        cursor.execute("""
            CREATE TABLE system_ingredients (
                system_ingredient_id INT AUTO_INCREMENT PRIMARY KEY,
                leverancier_id INT NOT NULL,
                naam VARCHAR(255) NOT NULL,
                categorie VARCHAR(100),
                eenheid VARCHAR(50) NOT NULL,
                prijs_per_eenheid DECIMAL(10,5) NOT NULL DEFAULT 0.00000,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (leverancier_id) REFERENCES leveranciers(leverancier_id) ON DELETE CASCADE,
                INDEX (leverancier_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        
        print("Table system_ingredients created successfully")
        connection.commit()
        return True
    except Error as e:
        print(f"Error creating table: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    create_system_ingredients_table()
