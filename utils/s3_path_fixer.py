import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv
import mysql.connector
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class S3PathFixer:
    def __init__(self):
        """Initialize S3 connection using environment variables"""
        self.bucket_name = os.getenv('S3_BUCKET')
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID') or os.getenv('S3_KEY')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY') or os.getenv('S3_SECRET')
        
        # Database connection info
        self.db_host = os.getenv('DB_HOST')
        self.db_name = os.getenv('DB_NAME')
        self.db_user = os.getenv('DB_USER')
        self.db_password = os.getenv('DB_PASSWORD')
        self.db_port = os.getenv('DB_PORT')
        
        # Check if we have all required credentials
        if not all([self.bucket_name, self.aws_access_key, self.aws_secret_key]):
            missing = []
            if not self.bucket_name:
                missing.append("S3_BUCKET")
            if not self.aws_access_key:
                missing.append("AWS_ACCESS_KEY_ID/S3_KEY")
            if not self.aws_secret_key:
                missing.append("AWS_SECRET_ACCESS_KEY/S3_SECRET")
            
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        # Create S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key
        )
        
    def get_db_connection(self):
        """Create a connection to the database"""
        try:
            connection = mysql.connector.connect(
                host=self.db_host,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                port=self.db_port
            )
            return connection
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            return None

    def list_problematic_files(self):
        """List files that appear to have double paths"""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
            
            problematic_files = []
            for item in response.get('Contents', []):
                key = item['Key']
                # Check if path contains duplicated filenames
                if '/' in key:
                    parts = key.split('/')
                    if len(parts) >= 2 and '.' in parts[-1]:
                        folder_name = parts[-2]
                        filename = parts[-1]
                        
                        # Check if filename is contained in the folder name
                        if filename in folder_name:
                            problematic_files.append(key)
            
            return problematic_files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []

    def fix_path(self, old_path, dry_run=True):
        """Fix a problematic path by copying to correct location and updating DB"""
        try:
            # Determine correct path (remove the duplicated filename)
            parts = old_path.split('/')
            if len(parts) < 2:
                logger.warning(f"Path {old_path} doesn't appear to be problematic")
                return False
                
            # If the path is like 'folder/filename.ext/filename.ext'
            if '.' in parts[-2] and '/' in old_path:
                correct_path = '/'.join(parts[:-1])
            else:
                # For paths like 'supplier_excel/Groenteboer_ingredienten.xlsx/differentfile.xlsx'
                # Extract the base folder and keep the original filename
                base_folder = parts[0]
                filename = parts[-1]
                correct_path = f"{base_folder}/{filename}"
            
            logger.info(f"Fixing path: {old_path} -> {correct_path}")
            
            if dry_run:
                logger.info(f"DRY RUN: Would copy {old_path} to {correct_path}")
                
                # Find DB records that reference this path
                db_records = self.find_db_references(old_path)
                for record in db_records:
                    logger.info(f"DRY RUN: Would update {record['table']}.{record['column']} for {record['id_column']}={record['id_value']} to {correct_path}")
                
                return {"old_path": old_path, "new_path": correct_path, "db_records": db_records}
            else:
                # Copy the file to new location
                copy_source = {'Bucket': self.bucket_name, 'Key': old_path}
                self.s3_client.copy_object(Bucket=self.bucket_name, CopySource=copy_source, Key=correct_path)
                
                # Update DB references
                db_records = self.find_db_references(old_path)
                update_count = self.update_db_references(db_records, correct_path)
                
                # Delete the old file
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=old_path)
                
                return {"old_path": old_path, "new_path": correct_path, "updated_records": update_count}
                
        except Exception as e:
            logger.error(f"Error fixing path {old_path}: {e}")
            return False

    def find_db_references(self, file_path):
        """Find database records that reference this file path"""
        conn = self.get_db_connection()
        if not conn:
            return []
            
        cursor = conn.cursor(dictionary=True)
        results = []
        
        try:
            # Check leveranciers table for excel_file_path
            cursor.execute("SELECT leverancier_id, excel_file_path FROM leveranciers WHERE excel_file_path = %s", (file_path,))
            for row in cursor.fetchall():
                results.append({
                    'table': 'leveranciers',
                    'column': 'excel_file_path',
                    'id_column': 'leverancier_id',
                    'id_value': row['leverancier_id'],
                    'current_value': row['excel_file_path']
                })
                
            # Check leveranciers table for logo_path
            cursor.execute("SELECT leverancier_id, logo_path FROM leveranciers WHERE logo_path = %s", (file_path,))
            for row in cursor.fetchall():
                results.append({
                    'table': 'leveranciers',
                    'column': 'logo_path',
                    'id_column': 'leverancier_id',
                    'id_value': row['leverancier_id'],
                    'current_value': row['logo_path']
                })
                
            # Add checks for other tables with file paths here
                
            return results
        except Exception as e:
            logger.error(f"Error finding DB references: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def update_db_references(self, records, new_path):
        """Update database references to use the new file path"""
        conn = self.get_db_connection()
        if not conn:
            return 0
            
        cursor = conn.cursor()
        update_count = 0
        
        try:
            for record in records:
                table = record['table']
                column = record['column']
                id_column = record['id_column']
                id_value = record['id_value']
                
                query = f"UPDATE {table} SET {column} = %s WHERE {id_column} = %s"
                cursor.execute(query, (new_path, id_value))
                update_count += cursor.rowcount
                
            conn.commit()
            return update_count
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating DB references: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()
            
    def fix_all_paths(self, dry_run=True):
        """Find and fix all problematic paths"""
        problematic_paths = self.list_problematic_files()
        
        logger.info(f"Found {len(problematic_paths)} problematic paths")
        
        results = []
        for path in problematic_paths:
            result = self.fix_path(path, dry_run)
            results.append(result)
            # Sleep briefly to avoid overloading the S3 API
            time.sleep(0.2)
            
        return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fix S3 paths with duplicated filenames.')
    parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without making changes')
    parser.add_argument('--path', help='Fix a specific path')
    
    args = parser.parse_args()
    
    fixer = S3PathFixer()
    
    if args.path:
        logger.info(f"Fixing specific path: {args.path}")
        result = fixer.fix_path(args.path, dry_run=args.dry_run)
        print(f"Result: {result}")
    else:
        logger.info("Fixing all problematic paths...")
        if args.dry_run:
            logger.info("DRY RUN: No changes will be made")
            
        results = fixer.fix_all_paths(dry_run=args.dry_run)
        
        logger.info(f"Processed {len(results)} paths")
        if args.dry_run:
            print("Paths that would be fixed:")
            for result in results:
                if result:
                    print(f"  {result['old_path']} -> {result['new_path']}")
                    if result.get('db_records'):
                        for record in result['db_records']:
                            print(f"    Update {record['table']}.{record['column']} for {record['id_column']}={record['id_value']}")
        else:
            fixed_count = sum(1 for r in results if r)
            print(f"Fixed {fixed_count} paths")
