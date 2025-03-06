import os
import sys
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_db_connection

load_dotenv()

def update_leveranciers_schema():
    """Update leveranciers table schema to make chef_id nullable"""
    conn = get_db_connection()
    if not conn:
        print("Database connection failed")
        return False
    
    cur = conn.cursor()
    try:
        # Make chef_id nullable
        cur.execute("""
            ALTER TABLE leveranciers 
            MODIFY COLUMN chef_id INT NULL
        """)
        conn.commit()
        print("✓ Successfully updated leveranciers table (chef_id is now nullable)")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating schema: {str(e)}")
        return False
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("\n===== Updating Leveranciers Schema =====\n")
    success = update_leveranciers_schema()
    print("Done!" if success else "Failed!")
