import boto3
from botocore.exceptions import ClientError
import os
import io
from dotenv import load_dotenv
import sys

# Load environment variables from .env file
load_dotenv()

class S3Diagnostic:
    def __init__(self):
        """Initialize S3 connection using environment variables"""
        self.bucket_name = os.getenv('S3_BUCKET')
        self.region_name = os.getenv('AWS_REGION', 'eu-central-1')  # Default to eu-central-1 if not specified
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID') or os.getenv('S3_KEY')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY') or os.getenv('S3_SECRET')
        
        # Check if we have all required credentials
        if not all([self.bucket_name, self.aws_access_key, self.aws_secret_key]):
            missing = []
            if not self.bucket_name:
                missing.append("S3_BUCKET")
            if not self.aws_access_key:
                missing.append("AWS_ACCESS_KEY_ID/S3_KEY")
            if not self.aws_secret_key:
                missing.append("AWS_SECRET_ACCESS_KEY/S3_SECRET")
            
            print(f"ERROR: Missing required environment variables: {', '.join(missing)}")
            print("Please ensure these are set in your .env file or environment.")
            sys.exit(1)
        
        print(f"Initializing S3 client for bucket: {self.bucket_name}")
        print(f"Using region: {self.region_name}")
        print(f"Using access key: {self.aws_access_key[:4]}...{self.aws_access_key[-4:]}")
        
        # Create S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=self.region_name,
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key
            )
            print("S3 client created successfully")
        except Exception as e:
            print(f"ERROR creating S3 client: {str(e)}")
            sys.exit(1)
    
    def test_connection(self):
        """Test basic connection to S3 bucket"""
        print("\n=== Testing S3 Connection ===")
        try:
            # Try to access bucket location
            location = self.s3_client.get_bucket_location(Bucket=self.bucket_name)
            print(f"SUCCESS: Connected to bucket {self.bucket_name}")
            print(f"Bucket location: {location.get('LocationConstraint', 'us-east-1')}")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            error_message = e.response.get('Error', {}).get('Message')
            print(f"ERROR: Connection test failed with code {error_code}: {error_message}")
            return False
        except Exception as e:
            print(f"ERROR: Unexpected error during connection test: {str(e)}")
            return False
    
    def list_bucket_contents(self, prefix=None):
        """List files in the S3 bucket, optionally filtered by prefix"""
        print(f"\n=== Listing Bucket Contents {f'with prefix: {prefix}' if prefix else ''} ===")
        try:
            if prefix:
                response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            else:
                response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
            
            contents = response.get('Contents', [])
            if not contents:
                print(f"No files found{f' with prefix {prefix}' if prefix else ' in bucket'}")
                return []
            
            print(f"Found {len(contents)} files:")
            for item in contents:
                print(f"- {item['Key']} ({item['Size']} bytes, last modified: {item['LastModified']})")
            
            return [item['Key'] for item in contents]
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            error_message = e.response.get('Error', {}).get('Message')
            print(f"ERROR: Could not list bucket contents. Code {error_code}: {error_message}")
            return []
        except Exception as e:
            print(f"ERROR: Unexpected error listing bucket contents: {str(e)}")
            return []
    
    def check_file_exists(self, file_path):
        """Check if a specific file exists in the S3 bucket"""
        print(f"\n=== Checking if file exists: {file_path} ===")
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            print(f"SUCCESS: File '{file_path}' exists in the bucket")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == '404':
                print(f"File '{file_path}' does not exist in the bucket")
            else:
                error_message = e.response.get('Error', {}).get('Message')
                print(f"ERROR: Failed to check file existence. Code {error_code}: {error_message}")
            return False
        except Exception as e:
            print(f"ERROR: Unexpected error checking file existence: {str(e)}")
            return False
    
    def upload_test_file(self, file_path, content="This is a test file."):
        """Upload a test file to the S3 bucket"""
        print(f"\n=== Uploading test file to: {file_path} ===")
        try:
            self.s3_client.put_object(
                Body=content,
                Bucket=self.bucket_name,
                Key=file_path,
                ContentType='text/plain'
            )
            print(f"SUCCESS: Test file uploaded to '{file_path}'")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            error_message = e.response.get('Error', {}).get('Message')
            print(f"ERROR: Failed to upload test file. Code {error_code}: {error_message}")
            return False
        except Exception as e:
            print(f"ERROR: Unexpected error uploading test file: {str(e)}")
            return False
    
    def download_file(self, file_path):
        """Try to download a file from the S3 bucket"""
        print(f"\n=== Downloading file: {file_path} ===")
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_path)
            content = response['Body'].read()
            size = len(content)
            content_type = response.get('ContentType', 'unknown')
            print(f"SUCCESS: File downloaded - {size} bytes, content type: {content_type}")
            
            # For text files, show a preview
            if content_type.startswith('text/') or size < 200:
                try:
                    preview = content.decode('utf-8')[:100]
                    print(f"Content preview: {preview}...")
                except UnicodeDecodeError:
                    print("Content is binary (not showing preview)")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            error_message = e.response.get('Error', {}).get('Message')
            print(f"ERROR: Failed to download file. Code {error_code}: {error_message}")
            return False
        except Exception as e:
            print(f"ERROR: Unexpected error downloading file: {str(e)}")
            return False
    
    def delete_file(self, file_path):
        """Delete a file from the S3 bucket"""
        print(f"\n=== Deleting file: {file_path} ===")
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_path)
            print(f"SUCCESS: File '{file_path}' deleted")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            error_message = e.response.get('Error', {}).get('Message')
            print(f"ERROR: Failed to delete file. Code {error_code}: {error_message}")
            return False
        except Exception as e:
            print(f"ERROR: Unexpected error deleting file: {str(e)}")
            return False
    
    def run_test_suite(self, test_file_path, problematic_path=None):
        """Run a series of tests to diagnose S3 issues"""
        print("\n========= S3 DIAGNOSTIC TEST SUITE =========\n")
        
        # Test 1: Basic connection
        if not self.test_connection():
            print("\nDiagnosis: Connection to S3 failed. Please check your credentials and network.")
            return
        
        # Test 2: List bucket contents
        print("\nListing all files in bucket...")
        self.list_bucket_contents()
        
        # Test 3: Check specific directory
        if problematic_path:
            folder = problematic_path.rsplit('/', 1)[0] + '/'
            print(f"\nListing contents of directory: {folder}")
            self.list_bucket_contents(prefix=folder)
            
            # Test 4: Check if problematic file exists
            self.check_file_exists(problematic_path)
        
        # Test 5: Upload test file
        if self.upload_test_file(test_file_path):
            # Test 6: Download the test file we just uploaded
            self.download_file(test_file_path)
            
            # Test 7: Delete the test file
            self.delete_file(test_file_path)
            
        print("\n========= END OF TEST SUITE =========")


def interactive_mode():
    """Run the diagnostic tool in interactive mode"""
    print("======= S3 Diagnostic Tool =======")
    
    s3 = S3Diagnostic()
    
    while True:
        print("\nAvailable commands:")
        print("1. Test connection")
        print("2. List bucket contents")
        print("3. Check if a file exists")
        print("4. Upload a test file")
        print("5. Download a file")
        print("6. Delete a file")
        print("7. Run full test suite")
        print("q. Quit")
        
        choice = input("\nEnter your choice (1-7 or q): ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == '1':
            s3.test_connection()
        elif choice == '2':
            prefix = input("Enter prefix (folder path) or leave empty for all: ").strip()
            s3.list_bucket_contents(prefix if prefix else None)
        elif choice == '3':
            path = input("Enter file path to check: ").strip()
            s3.check_file_exists(path)
        elif choice == '4':
            path = input("Enter path for test file: ").strip()
            s3.upload_test_file(path)
        elif choice == '5':
            path = input("Enter path of file to download: ").strip()
            s3.download_file(path)
        elif choice == '6':
            path = input("Enter path of file to delete: ").strip()
            s3.delete_file(path)
        elif choice == '7':
            test_file = input("Enter path for test file: ").strip() or "test/diagnostic_test_file.txt"
            problematic_path = input("Enter problematic file path (optional): ").strip()
            s3.run_test_suite(test_file, problematic_path if problematic_path else None)
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    interactive_mode()
