import os
import sys
import re
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_db_connection

load_dotenv()

def is_valid_email(email):
    """Controleer of een email geldig is"""
    # Eenvoudige regex voor email validatie
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

def update_admin_emails(conn):
    """Update alle admin accounts om ervoor te zorgen dat ze een email hebben"""
    cursor = conn.cursor(dictionary=True)
    try:
        # Eerst voegen we een email constraint toe
        try:
            cursor.execute("ALTER TABLE admins MODIFY email VARCHAR(100) NOT NULL UNIQUE")
            print("✓ Email kolom bijgewerkt naar NOT NULL UNIQUE")
        except Exception as e:
            print(f"Fout bij wijzigen email kolom: {str(e)}")

        # Haal admins op zonder email
        cursor.execute("SELECT admin_id, username FROM admins WHERE email IS NULL OR email = ''")
        admins_without_email = cursor.fetchall()
        
        if not admins_without_email:
            print("✓ Alle admin accounts hebben al een email adres")
            return True
            
        print(f"Gevonden: {len(admins_without_email)} admin accounts zonder email")
        
        for admin in admins_without_email:
            print(f"\nAdmin: {admin['username']} (ID: {admin['admin_id']})")
            while True:
                email = input("Voer een geldig email adres in voor deze admin: ")
                if not email:
                    print("Email is verplicht.")
                    continue
                    
                if not is_valid_email(email):
                    print("Ongeldig email formaat. Probeer opnieuw.")
                    continue
                    
                # Controleer of email al in gebruik is
                cursor.execute("SELECT admin_id FROM admins WHERE email = %s AND admin_id != %s", 
                            (email, admin['admin_id']))
                if cursor.fetchone():
                    print("Dit email adres is al in gebruik. Kies een ander adres.")
                    continue
                    
                # Update de admin
                cursor.execute("UPDATE admins SET email = %s WHERE admin_id = %s", 
                            (email, admin['admin_id']))
                conn.commit()
                print(f"✓ Email bijgewerkt voor admin {admin['username']}")
                break
                
        return True
            
    except Exception as e:
        conn.rollback()
        print(f"Fout bij updaten admins: {str(e)}")
        return False
    finally:
        cursor.close()

def main():
    print("\n===== E-Chef Admin Email Update =====\n")
    
    # Maak verbinding met de database
    conn = get_db_connection()
    if not conn:
        print("Kan geen verbinding maken met de database. Controleer je .env instellingen.")
        return
    
    try:
        update_admin_emails(conn)
        print("\n✓ Alle admin accounts hebben nu een email adres")
    except KeyboardInterrupt:
        print("\nGeannuleerd.")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
