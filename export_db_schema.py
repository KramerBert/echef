import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

# Laad de .env-variabelen
load_dotenv()

# Haal de databaseconfiguratie uit de .env-variabelen
db_host = os.getenv('MYSQL_HOST', '127.0.0.1')  # Gebruik 127.0.0.1 in plaats van localhost
db_user = os.getenv('MYSQL_USER')
db_password = os.getenv('MYSQL_PASSWORD')
db_name = os.getenv('MYSQL_DB')

# Controleer of de vereiste omgevingsvariabelen zijn geladen
if not all([db_host, db_user, db_password, db_name]):
    raise ValueError("Eén of meer databaseconfiguratievariabelen ontbreken. Controleer het .env-bestand.")

try:
    # Maak verbinding met de database
    with mysql.connector.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name
    ) as connection:
        
        with connection.cursor() as cursor:
            # Haal de tabellen op
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()

            # Open een bestand om de schema-informatie op te slaan
            with open("db_schema.txt", "w") as file:
                for table in tables:
                    table_name = table[0]
                    file.write(f"Table: {table_name}\n")
                    
                    # Haal de kolommen van de tabel op (gebruik parameterbinding voor veiligheid)
                    cursor.execute("DESCRIBE `{}`".format(table_name))
                    columns = cursor.fetchall()
                    
                    for column in columns:
                        file.write(f"  {column[0]} {column[1]}\n")
                    
                    file.write("\n")

            print("Database schema is succesvol geëxporteerd naar db_schema.txt")

except Error as e:
    print(f"Fout bij databaseverbinding: {e}")

except Exception as e:
    print(f"Onverwachte fout: {e}")
