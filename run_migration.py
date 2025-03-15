import sys
import os

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the migration
from migrations.create_system_ingredients_table import create_system_ingredients_table

if __name__ == "__main__":
    print("Running migration to create system_ingredients table...")
    success = create_system_ingredients_table()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
