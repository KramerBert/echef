from sqlalchemy import create_engine, inspect, MetaData, text
import sys
import os
from dotenv import load_dotenv

# Laad de .env file
load_dotenv()

# Haal database configuratie uit .env
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_NAME = os.getenv('DB_NAME')

# MySQL specifieke URI
DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def check_database():
    """Controleer database op verschillende aspecten"""
    try:
        engine = create_engine(DATABASE_URI)
        inspector = inspect(engine)
        
        print("\n🔍 Start Database Controle...\n")

        # 1. MySQL versie en status
        with engine.connect() as conn:
            version = conn.execute(text("SELECT VERSION()")).scalar()
            print(f"MySQL Versie: {version}")
            
            # Check database status
            status = conn.execute(text("SHOW STATUS WHERE Variable_name = 'Uptime'")).fetchone()
            print(f"Database Uptime: {int(status[1])/3600:.1f} uren")

        # 2. Controleer tabellen
        print("\n📊 Tabel Overzicht:")
        for table_name in inspector.get_table_names():
            print(f"\n➤ Tabel: {table_name}")
            
            # Tabel info
            with engine.connect() as conn:
                # Aantal rijen
                result = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
                row_count = result.scalar()
                print(f"   Aantal rijen: {row_count}")
                
                # Tabel grootte
                result = conn.execute(text(f"""
                    SELECT 
                        ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
                    FROM information_schema.tables
                    WHERE table_schema = '{DB_NAME}'
                    AND table_name = '{table_name}'
                """))
                size = result.scalar()
                print(f"   Grootte: {size} MB")
            
            # Kolommen
            columns = inspector.get_columns(table_name)
            print(f"   Kolommen: {len(columns)}")
            for column in columns:
                nullable = "NULL toegestaan" if column['nullable'] else "NOT NULL"
                print(f"   - {column['name']}: {column['type']} ({nullable})")

            # Indexes
            indexes = inspector.get_indexes(table_name)
            if indexes:
                print("   Indexes:")
                for index in indexes:
                    unique = "UNIQUE " if index['unique'] else ""
                    print(f"   - {unique}INDEX op {index['column_names']}")

        # 3. Database statistieken
        print("\n📈 Database Statistieken:")
        with engine.connect() as conn:
            # Totale grootte
            result = conn.execute(text(f"""
                SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2)
                FROM information_schema.tables
                WHERE table_schema = '{DB_NAME}'
            """))
            total_size = result.scalar()
            print(f"Totale database grootte: {total_size} MB")
            
            # Buffer pool info
            result = conn.execute(text("SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_%'"))
            pool_stats = result.fetchall()
            print("\nInnoDB Buffer Pool Status:")
            for stat in pool_stats:
                if stat[0] in ['Innodb_buffer_pool_reads', 'Innodb_buffer_pool_wait_free']:
                    print(f"   {stat[0]}: {stat[1]}")

        # 4. Performance checks
        print("\n⚡ Performance Checks:")
        with engine.connect() as conn:
            # Langzame queries check
            slow_queries = conn.execute(text("SHOW GLOBAL STATUS LIKE 'Slow_queries'")).fetchone()
            print(f"Aantal trage queries: {slow_queries[1]}")
            
            # Table scans
            result = conn.execute(text("""
                SHOW GLOBAL STATUS 
                WHERE Variable_name IN ('Select_scan', 'Select_full_join')
            """))
            for stat in result:
                print(f"{stat[0]}: {stat[1]}")

    except Exception as e:
        print(f"❌ Database fout: {str(e)}")
        print("\nControleer of:")
        print("1. MySQL service draait")
        print("2. Credentials in .env correct zijn")
        print("3. Database bestaat")
        print(f"4. User '{DB_USER}' toegang heeft tot '{DB_NAME}'")

if __name__ == "__main__":
    check_database()
