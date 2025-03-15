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

def verify_system_ingredients_table():
    """Verify the system_ingredients table structure and data"""
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database")
        return False
        
    cursor = connection.cursor(dictionary=True)
    try:
        # Check if table exists
        cursor.execute("SHOW TABLES LIKE 'system_ingredients'")
        if not cursor.fetchone():
            print("Table system_ingredients doesn't exist!")
            return False
            
        # Get table structure
        cursor.execute("DESCRIBE system_ingredients")
        columns = {row['Field']: row for row in cursor.fetchall()}
        print("Table structure:")
        for column, info in columns.items():
            print(f"  {column}: {info['Type']} {info.get('Null', '')} {info.get('Key', '')}")
        
        # Check for required columns
        required_columns = [
            'system_ingredient_id', 'leverancier_id', 'naam', 
            'categorie', 'eenheid', 'prijs_per_eenheid'
        ]
        
        missing_columns = [col for col in required_columns if col not in columns]
        if missing_columns:
            print(f"Missing required columns: {missing_columns}")
            return False
            
        # Check for data
        cursor.execute("SELECT COUNT(*) as count FROM system_ingredients")
        count = cursor.fetchone()['count']
        print(f"System ingredients table has {count} records")
        
        # Get sample data
        if count > 0:
            cursor.execute("SELECT * FROM system_ingredients LIMIT 5")
            samples = cursor.fetchall()
            print("\nSample data:")
            for sample in samples:
                print(f"  {sample}")
        
        # Get suppliers with ingredients
        cursor.execute("""
            SELECT l.leverancier_id, l.naam, COUNT(si.system_ingredient_id) as ingredient_count
            FROM leveranciers l
            LEFT JOIN system_ingredients si ON l.leverancier_id = si.leverancier_id
            WHERE l.is_admin_created = TRUE
            GROUP BY l.leverancier_id
            ORDER BY ingredient_count DESC
        """)
        suppliers = cursor.fetchall()
        print("\nSystem suppliers and their ingredient counts:")
        for supplier in suppliers:
            print(f"  ID: {supplier['leverancier_id']}, Name: {supplier['naam']}, "
                  f"Ingredients: {supplier['ingredient_count']}")
        
        return True
    except Error as e:
        print(f"Error verifying table: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

def debug_import_process(supplier_id):
    """Debug the import process for a specific supplier"""
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database")
        return False
        
    cursor = connection.cursor(dictionary=True)
    try:
        # Check if supplier exists
        cursor.execute("SELECT * FROM leveranciers WHERE leverancier_id = %s", (supplier_id,))
        supplier = cursor.fetchone()
        if not supplier:
            print(f"Supplier with ID {supplier_id} not found!")
            return False
            
        print(f"Supplier found: {supplier['naam']} (ID: {supplier_id})")
            
        # Get supplier's ingredients
        cursor.execute("SELECT * FROM system_ingredients WHERE leverancier_id = %s", (supplier_id,))
        ingredients = cursor.fetchall()
        
        print(f"Found {len(ingredients)} ingredients for this supplier")
        
        if len(ingredients) == 0:
            print("No ingredients found - this is why import is showing 0 ingredients")
        else:
            print("\nFirst 5 ingredients:")
            for i, ingredient in enumerate(ingredients[:5]):
                print(f"  {i+1}. {ingredient['naam']} ({ingredient['eenheid']}): {ingredient['prijs_per_eenheid']}")
        
        return True
    except Error as e:
        print(f"Error debugging import: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

def add_sample_ingredient(supplier_id):
    """Add a sample ingredient to test system_ingredients for a supplier"""
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database")
        return False
        
    cursor = connection.cursor()
    try:
        # Add a sample ingredient
        cursor.execute("""
            INSERT INTO system_ingredients 
            (leverancier_id, naam, categorie, eenheid, prijs_per_eenheid)
            VALUES (%s, %s, %s, %s, %s)
        """, (supplier_id, "Test Ingredient", "Overig", "stuk", 1.00))
        
        connection.commit()
        print(f"Added test ingredient for supplier {supplier_id}")
        return True
    except Error as e:
        connection.rollback()
        print(f"Error adding sample ingredient: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    verify_system_ingredients_table()
    
    # Ask if user wants to debug a specific supplier
    debug_option = input("\nDo you want to debug a specific supplier? (y/n): ")
    if debug_option.lower() == 'y':
        supplier_id = int(input("Enter supplier ID: "))
        debug_import_process(supplier_id)
        
        # Ask if user wants to add a test ingredient
        add_test = input("\nDo you want to add a test ingredient for this supplier? (y/n): ")
        if add_test.lower() == 'y':
            add_sample_ingredient(supplier_id)
            print("Now try the import again to see if it works with the test ingredient")
