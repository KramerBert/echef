import os
import sys
import getpass
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mysql.connector
from urllib.parse import urlparse

load_dotenv()

def get_production_db_connection():
    """Connect to the production JawsDB database on Heroku"""
    db_url = os.getenv("JAWSDB_URL")
    if not db_url:
        print("Error: JAWSDB_URL is not defined in your environment variables")
        return None
    
    try:
        url = urlparse(db_url)
        conn = mysql.connector.connect(
            host=url.hostname,
            user=url.username,
            password=url.password,
            database=url.path[1:],
            port=url.port
        )
        print("✓ Connected to production database (JawsDB on Heroku)")
        return conn
    except Exception as e:
        print(f"Error connecting to production database: {str(e)}")
        return None

# Import functions from the original create_admin script
from scripts.create_admin import create_admin_table, create_admin_user

def main():
    print("\n===== E-Chef Admin Gebruiker Aanmaken (PRODUCTIE) =====\n")
    print("LET OP: Je gaat een admin-gebruiker aanmaken op de PRODUCTIE database!")
    confirm = input("Weet je zeker dat je door wilt gaan? (j/n): ")
    
    if confirm.lower() != 'j':
        print("Geannuleerd.")
        return
    
    # Maak verbinding met de productiedatabase
    conn = get_production_db_connection()
    if not conn:
        print("Kan geen verbinding maken met de productiedatabase.")
        return
    
    # Maak de admin tabel aan als die niet bestaat
    if not create_admin_table(conn):
        conn.close()
        return
    
    # Vraag om admin gegevens
    try:
        username = input("Voer admin gebruikersnaam in: ")
        if not username:
            print("Gebruikersnaam is verplicht.")
            return
        
        email = input("Voer admin email in: ")
        if not email:
            print("Email is verplicht.")
            return
        
        password = getpass.getpass("Voer admin wachtwoord in: ")
        if not password:
            print("Wachtwoord is verplicht.")
            return
        
        password_confirm = getpass.getpass("Bevestig admin wachtwoord: ")
        if password != password_confirm:
            print("Wachtwoorden komen niet overeen!")
            return
        
        # Maak de admin gebruiker aan
        create_admin_user(conn, username, password, email)
        
    except KeyboardInterrupt:
        print("\nGeannuleerd.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
