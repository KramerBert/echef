import os
import sys
import getpass
import argparse
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_db_connection
import mysql.connector
from urllib.parse import urlparse

load_dotenv()

def connect_to_production_db():
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

def create_admin_table(conn):
    """Maak de admins tabel aan als deze nog niet bestaat"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        print("✓ Admin tabel is gecontroleerd/aangemaakt")
        return True
    except Exception as e:
        print(f"Fout bij maken admin tabel: {str(e)}")
        return False
    finally:
        cursor.close()

def create_admin_user(conn, username, password, email):
    """Maak een nieuwe admin gebruiker aan"""
    cursor = conn.cursor(dictionary=True)
    try:
        # Controleer of gebruikersnaam of email al bestaat
        cursor.execute("SELECT username FROM admins WHERE username = %s OR email = %s", (username, email))
        existing_admin = cursor.fetchone()
        
        if existing_admin:
            print(f"Admin gebruiker of email bestaat al!")
            return False
        
        # Hash het wachtwoord
        password_hash = generate_password_hash(password)
        
        # Voeg de admin toe
        cursor.execute("""
        INSERT INTO admins (username, password_hash, email)
        VALUES (%s, %s, %s)
        """, (username, password_hash, email))
        
        conn.commit()
        print(f"✓ Admin gebruiker '{username}' met email '{email}' succesvol aangemaakt!")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Fout bij aanmaken admin: {str(e)}")
        return False
    finally:
        cursor.close()

def main():
    parser = argparse.ArgumentParser(description='Create admin user for E-Chef')
    parser.add_argument('--production', action='store_true', help='Connect to production database')
    args = parser.parse_args()

    print("\n===== E-Chef Admin Gebruiker Aanmaken =====\n")
    
    # Connect to the appropriate database
    if args.production:
        conn = connect_to_production_db()
    else:
        conn = get_db_connection()
        
    if not conn:
        print("Unable to connect to database. Check your configuration.")
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
