import sys
import os

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the migrations
from migrations.add_missing_columns_to_system_ingredients import add_missing_columns

if __name__ == "__main__":
    print("Running migration to add missing columns to system_ingredients table...")
    success = add_missing_columns()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
