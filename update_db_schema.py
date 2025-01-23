import mysql.connector
from dotenv import load_dotenv
import os

# Laad de .env-variabelen
load_dotenv()

# Haal de databaseconfiguratie uit de .env-variabelen en zorg ervoor dat ze correct zijn geladen
try:
    db_config = {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DB"),
        "port": int(os.getenv("MYSQL_PORT", 3306))
    }

    if not all(db_config.values()):
        raise ValueError("Een of meer databaseconfiguratievariabelen ontbreken.")
    
    # Maak verbinding met de database
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    # Maak de tabel 'units' aan als deze nog niet bestaat
    create_units_table_query = """
    CREATE TABLE IF NOT EXISTS units (
        id INT AUTO_INCREMENT PRIMARY KEY,
        naam VARCHAR(50) NOT NULL
    );
    """
    cursor.execute(create_units_table_query)
    connection.commit()
    print("Tabel 'units' is succesvol aangemaakt.")

    # Voeg enkele standaard eenheden toe aan de tabel 'units'
    insert_units_query = """
    INSERT INTO units (naam) VALUES
    ('gram'),
    ('ons'),
    ('pond'),
    ('kilogram'),
    ('milliliter'),
    ('centiliter'),
    ('deciliter'),
    ('liter'),
    ('theelepel'),
    ('eetlepel'),
    ('kopje'),
    ('glas'),
    ('fles'),
    ('blik'),
    ('pak'),
    ('kan'),
    ('stuk'),
    ('snee'),
    ('plak'),
    ('takje'),
    ('blad'),
    ('bol'),
    ('teentje'),
    ('stronk'),
    ('bosje'),
    ('scheutje'),
    ('snufje'),
    ('mespunt'),
    ('doos'),
    ('zak'),
    ('rol'),
    ('reep'),
    ('klontje'),
    ('druppel'),
    ('blokje'),
    ('kilo'),
    ('pond'),
    ('ons'),
    ('beker'),
    ('cup'),
    ('pint'),
    ('quart'),
    ('gallon'),
    ('ounce'),
    ('pound')
    ON DUPLICATE KEY UPDATE naam=VALUES(naam);
    """
    cursor.execute(insert_units_query)
    connection.commit()
    print("Standaard eenheden zijn succesvol toegevoegd aan de tabel 'units'.")

    # Maak de tabel 'categories' aan als deze nog niet bestaat
    create_categories_table_query = """
    CREATE TABLE IF NOT EXISTS categories (
        id INT AUTO_INCREMENT PRIMARY KEY,
        naam VARCHAR(50) NOT NULL
    );
    """
    cursor.execute(create_categories_table_query)
    connection.commit()
    print("Tabel 'categories' is succesvol aangemaakt.")

    # Voeg enkele standaard categorieën toe aan de tabel 'categories'
    insert_categories_query = """
    INSERT INTO categories (naam) VALUES
    ('groenten'),
    ('vlees'),
    ('vis'),
    ('zuivel'),
    ('fruit'),
    ('granen'),
    ('kruiden'),
    ('overig'),
    ('sauzen'),
    ('soepen'),
    ('desserts'),
    ('dranken'),
    ('brood'),
    ('pasta'),
    ('rijst'),
    ('peulvruchten'),
    ('noten'),
    ('zaden'),
    ('specerijen'),
    ('olie'),
    ('azijn'),
    ('conserven'),
    ('diepvries'),
    ('kant-en-klaar'),
    ('snacks'),
    ('ontbijtgranen'),
    ('zuivelvervangers'),
    ('vleesvervangers'),
    ('bakproducten'),
    ('snoep'),
    ('chocolade'),
    ('koffie'),
    ('thee'),
    ('alcoholische dranken'),
    ('non-alcoholische dranken')
    ON DUPLICATE KEY UPDATE naam=VALUES(naam);
    """
    cursor.execute(insert_categories_query)
    connection.commit()
    print("Standaard categorieën zijn succesvol toegevoegd aan de tabel 'categories'.")

    # Controleer of de kolom 'chef_id' al bestaat in de 'gerecht' tabel
    check_column_query = """
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'gerecht' 
    AND COLUMN_NAME = 'chef_id' 
    AND TABLE_SCHEMA = DATABASE();
    """

    cursor.execute(check_column_query)
    column_exists = cursor.fetchone()[0]

    if column_exists == 0:
        alter_table_query_gerecht = """
        ALTER TABLE gerecht
        ADD COLUMN chef_id INT;
        """
        cursor.execute(alter_table_query_gerecht)
        connection.commit()
        print("Kolom chef_id is succesvol toegevoegd aan de tabel gerecht.")

        # Update bestaande rijen met een standaard chef_id (bijvoorbeeld 1)
        update_existing_rows_query = """
        UPDATE gerecht
        SET chef_id = 1
        WHERE chef_id IS NULL;
        """
        cursor.execute(update_existing_rows_query)
        connection.commit()
        print("Bestaande rijen in de tabel gerecht zijn bijgewerkt met een standaard chef_id.")

        # Voeg de foreign key constraint toe
        add_foreign_key_query = """
        ALTER TABLE gerecht
        ADD CONSTRAINT fk_chef FOREIGN KEY (chef_id) REFERENCES chefs(id);
        """
        cursor.execute(add_foreign_key_query)
        connection.commit()
        print("Foreign key constraint is succesvol toegevoegd aan de tabel gerecht.")
    else:
        print("Kolom chef_id bestaat al in de tabel gerecht.")

    # Maak de tabel 'gerecht_ingredient' aan als deze nog niet bestaat
    create_gerecht_ingredient_table_query = """
    CREATE TABLE IF NOT EXISTS gerecht_ingredient (
        gerecht_id INT,
        ingredient_id INT,
        hoeveelheid VARCHAR(255),
        chef_id INT,
        PRIMARY KEY (gerecht_id, ingredient_id),
        FOREIGN KEY (gerecht_id) REFERENCES gerecht(id),
        FOREIGN KEY (ingredient_id) REFERENCES ingredient(id),
        FOREIGN KEY (chef_id) REFERENCES chefs(id)
    );
    """
    cursor.execute(create_gerecht_ingredient_table_query)
    connection.commit()
    print("Tabel 'gerecht_ingredient' is succesvol aangemaakt.")

    # Controleer of de kolom 'chef_id' al bestaat in de 'gerecht_ingredient' tabel
    check_column_query_gerecht_ingredient = """
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'gerecht_ingredient' 
    AND COLUMN_NAME = 'chef_id' 
    AND TABLE_SCHEMA = DATABASE();
    """

    cursor.execute(check_column_query_gerecht_ingredient)
    column_exists_gerecht_ingredient = cursor.fetchone()[0]

    if column_exists_gerecht_ingredient == 0:
        alter_table_query_gerecht_ingredient = """
        ALTER TABLE gerecht_ingredient
        ADD COLUMN chef_id INT;
        """
        cursor.execute(alter_table_query_gerecht_ingredient)
        connection.commit()
        print("Kolom chef_id is succesvol toegevoegd aan de tabel gerecht_ingredient.")

        # Voeg de foreign key constraint toe
        add_foreign_key_query_gerecht_ingredient = """
        ALTER TABLE gerecht_ingredient
        ADD CONSTRAINT fk_chef_gerecht_ingredient FOREIGN KEY (chef_id) REFERENCES chefs(id);
        """
        cursor.execute(add_foreign_key_query_gerecht_ingredient)
        connection.commit()
        print("Foreign key constraint is succesvol toegevoegd aan de tabel gerecht_ingredient.")
    else:
        print("Kolom chef_id bestaat al in de tabel gerecht_ingredient.")

except mysql.connector.Error as err:
    print(f"Fout bij databaseverbinding of query: {err}")

except ValueError as ve:
    print(f"Configuratiefout: {ve}")

finally:
    if 'cursor' in locals() and cursor is not None:
        cursor.close()
    if 'connection' in locals() and connection.is_connected():
        connection.close()
