import sys
import os

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the migration
from migrations.remove_allergenen_column import remove_allergenen_column

if __name__ == "__main__":
    print("Running migration to remove allergenen column from system_ingredients table...")
    success = remove_allergenen_column()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
