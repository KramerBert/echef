import os
import sys
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_db_connection

load_dotenv()

def update_leveranciers_table():
    """Add admin supplier fields to leveranciers table"""
    conn = get_db_connection()
    if not conn:
        print("Database connection failed")
        return False
    
    cur = conn.cursor()
    try:
        # Check if columns already exist
        cur.execute("SHOW COLUMNS FROM leveranciers LIKE 'is_admin_created'")
        if not cur.fetchone():
            cur.execute("""
                ALTER TABLE leveranciers 
                ADD COLUMN is_admin_created BOOLEAN DEFAULT FALSE,
                ADD COLUMN banner_image VARCHAR(255) NULL,
                ADD COLUMN has_standard_list BOOLEAN DEFAULT FALSE
            """)
            print("✓ Leveranciers table updated with admin fields")
        else:
            print("✓ Admin fields already exist in leveranciers table")
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating schema: {str(e)}")
        return False
    finally:
        cur.close()
        conn.close()

def main():
    print("\n===== Updating Schema for Admin Suppliers =====\n")
    update_leveranciers_table()
    print("\nDone!")

if __name__ == "__main__":
    main()
