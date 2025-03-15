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

def list_system_suppliers():
    """List all system suppliers"""
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database")
        return
        
    cursor = connection.cursor(dictionary=True)
    try:
        # Get system suppliers
        cursor.execute("""
            SELECT leverancier_id, naam, contact 
            FROM leveranciers 
            WHERE is_admin_created = TRUE
            ORDER BY naam
        """)
        suppliers = cursor.fetchall()
        
        print("\nBeschikbare systeemleveranciers:")
        print("---------------------------------")
        for supplier in suppliers:
            print(f"ID: {supplier['leverancier_id']}, Naam: {supplier['naam']}, Contact: {supplier.get('contact', 'N/A')}")
        
    except Error as e:
        print(f"Error listing suppliers: {e}")
    finally:
        cursor.close()
        connection.close()

def add_ingredient_to_system_supplier():
    """Add an ingredient to a system supplier"""
    supplier_id = input("\nVoer leverancier ID in: ")
    naam = input("Naam van het ingredient: ")
    categorie = input("Categorie (bijv. 'Vlees', 'Groente', etc.): ")
    eenheid = input("Eenheid (bijv. 'kg', 'stuk', etc.): ")
    prijs = input("Prijs per eenheid (gebruik punt als decimaal scheidingsteken): ")
    
    # Validate inputs
    try:
        supplier_id = int(supplier_id)
        prijs = float(prijs)
    except ValueError:
        print("Fout: ID moet een geheel getal zijn, prijs moet een numerieke waarde zijn.")
        return
    
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database")
        return
        
    cursor = connection.cursor()
    try:
        # First check if the supplier exists and is a system supplier
        cursor.execute("""
            SELECT leverancier_id FROM leveranciers 
            WHERE leverancier_id = %s AND is_admin_created = TRUE
        """, (supplier_id,))
        
        if not cursor.fetchone():
            print(f"Fout: Systeemleverancier met ID {supplier_id} niet gevonden")
            return
        
        # Add the ingredient
        cursor.execute("""
            INSERT INTO system_ingredients 
            (leverancier_id, naam, categorie, eenheid, prijs_per_eenheid)
            VALUES (%s, %s, %s, %s, %s)
        """, (supplier_id, naam, categorie, eenheid, prijs))
        
        connection.commit()
        print(f"Ingredient '{naam}' succesvol toegevoegd aan leverancier ID {supplier_id}")
        
    except Error as e:
        connection.rollback()
        print(f"Error adding ingredient: {e}")
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    print("===== INGREDIËNTEN TOEVOEGEN AAN SYSTEEMLEVERANCIER =====")
    print("Dit script helpt je om ingrediënten toe te voegen aan een systeemleverancier.")
    
    while True:
        print("\nMenu:")
        print("1. Bekijk systeemleveranciers")
        print("2. Voeg ingredient toe aan systeemleverancier")
        print("3. Afsluiten")
        
        choice = input("\nMaak een keuze (1-3): ")
        
        if choice == "1":
            list_system_suppliers()
        elif choice == "2":
            add_ingredient_to_system_supplier()
        elif choice == "3":
            break
        else:
            print("Ongeldige keuze, probeer opnieuw.")

    print("\nProgramma afgesloten.")
