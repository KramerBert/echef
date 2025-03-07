import os
import boto3
from botocore.exceptions import ClientError
import logging
from flask import current_app
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

class FileStorage:
    """
    Abstraction for file storage that can use either local filesystem 
    or Amazon S3 based on configuration
    """
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app configuration"""
        self.app = app
        # Get settings from app config
        self.use_s3 = app.config.get('USE_S3', False)
        
        if self.use_s3:
            self.s3_bucket = app.config.get('S3_BUCKET')
            self.s3_location = app.config.get('S3_LOCATION')
            self.s3_client = boto3.client(
                's3',
                region_name='eu-west-1',  # Add explicit region - use the region where your bucket is located
                aws_access_key_id=app.config.get('S3_KEY'),
                aws_secret_access_key=app.config.get('S3_SECRET'),
                config=boto3.session.Config(signature_version='s3v4')  # Use the latest signature version
            )
            logger.info(f"Initialized S3 storage with bucket: {self.s3_bucket}")
        else:
            logger.info("Using local file storage")
    
    def save_file(self, file, directory, filename=None):
        """
        Save a file to storage (local or S3)
        
        Args:
            file: FileStorage object from request.files
            directory: Directory path/prefix where file should be saved
            filename: Optional filename, if None, uses the original secure filename
            
        Returns:
            Relative path to the saved file (for database storage)
        """
        if not filename:
            filename = secure_filename(file.filename)
            
        # Full path to store in database
        relative_path = os.path.join(directory, filename).replace('\\', '/')
            
        if self.use_s3:
            try:
                # For S3, we need to reset the file pointer and read content
                file.seek(0)
                self.s3_client.upload_fileobj(
                    file,
                    self.s3_bucket,
                    relative_path,
                    ExtraArgs={
                        'ContentType': file.content_type
                    }
                )
                
                # Return the S3 URL or just the path if we'll construct URLs separately
                return relative_path
                
            except ClientError as e:
                logger.error(f"Error uploading to S3: {str(e)}")
                return None
        else:
            # For local storage, create directory if needed
            full_path = os.path.join(current_app.root_path, 'static', relative_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Save file locally
            file.save(full_path)
            return relative_path
    
    def delete_file(self, file_path):
        """
        Delete a file from storage
        
        Args:
            file_path: Relative path to the file (as stored in database)
            
        Returns:
            True if successful, False otherwise
        """
        if not file_path:
            logger.warning("Attempted to delete a file with empty path")
            return False
            
        # Normalize the file path by removing any leading/trailing whitespace
        # and ensuring consistent slash direction
        file_path = file_path.strip().replace('\\', '/')
        
        # Remove any leading slash which would cause issues with S3 keys
        if file_path.startswith('/'):
            file_path = file_path[1:]
            
        logger.info(f"Attempting to delete normalized file path: {file_path}")
        logger.info(f"Storage mode: {'S3' if self.use_s3 else 'Local'}")
            
        if self.use_s3:
            try:
                logger.info(f"Deleting from S3 bucket '{self.s3_bucket}', key: '{file_path}'")
                
                # First check if the file exists with explicit error handling
                try:
                    response = self.s3_client.head_object(Bucket=self.s3_bucket, Key=file_path)
                    logger.info(f"File exists in S3, proceeding with deletion. Response: {response}")
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code')
                    if error_code == '404':
                        logger.warning(f"File not found in S3 (404): {file_path}")
                        return False
                    else:
                        logger.error(f"Error checking file existence in S3: {str(e)}")
                        logger.error(f"Error code: {error_code}")
                        logger.error(f"Full error response: {e.response}")
                        return False
                        
                # Now delete the file with better error info
                try:
                    response = self.s3_client.delete_object(
                        Bucket=self.s3_bucket,
                        Key=file_path
                    )
                    logger.info(f"S3 deletion successful. Response: {response}")
                    return True
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code')
                    logger.error(f"Error deleting from S3: {str(e)}")
                    logger.error(f"Error code: {error_code}")
                    logger.error(f"Full error response: {e.response}")
                    return False
                    
            except Exception as e:
                logger.error(f"Unexpected error in S3 delete operation: {str(e)}")
                if hasattr(e, 'response'):
                    logger.error(f"Error response details: {e.response}")
                return False
        else:
            # Delete from local filesystem
            full_path = os.path.join(current_app.root_path, 'static', file_path)
            logger.info(f"Deleting from local filesystem: {full_path}")
            
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                    logger.info(f"Local file deleted successfully")
                    return True
                except PermissionError as e:
                    logger.error(f"Permission error deleting local file: {str(e)}")
                    return False
                except OSError as e:
                    logger.error(f"OS error deleting local file: {str(e)}")
                    return False
                except Exception as e:
                    logger.error(f"Unexpected error deleting local file: {str(e)}")
                    return False
            else:
                logger.warning(f"File not found for deletion: {full_path}")
                return False
    
    def get_file_url(self, file_path):
        """
        Get public URL for a file
        
        Args:
            file_path: Relative path to the file (as stored in database)
            
        Returns:
            Full URL to the file
        """
        if not file_path:
            return None
            
        if self.use_s3:
            # Generate direct S3 URL with proper format
            # Remove any leading slashes to avoid double slashes in the URL
            clean_path = file_path.lstrip('/')
            return f"{self.s3_location}/{clean_path}"
        else:
            # For local files, return the static URL
            return f"/static/{file_path}"
