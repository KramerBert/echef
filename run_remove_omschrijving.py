import sys
import os

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the migration
from migrations.remove_omschrijving_column import remove_omschrijving_column

if __name__ == "__main__":
    print("Running migration to remove omschrijving column from system_ingredients table...")
    success = remove_omschrijving_column()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
