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
                aws_access_key_id=app.config.get('S3_KEY'),
                aws_secret_access_key=app.config.get('S3_SECRET')
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
            return False
            
        if self.use_s3:
            try:
                self.s3_client.delete_object(
                    Bucket=self.s3_bucket,
                    Key=file_path
                )
                return True
            except ClientError as e:
                logger.error(f"Error deleting from S3: {str(e)}")
                return False
        else:
            # Delete from local filesystem
            full_path = os.path.join(current_app.root_path, 'static', file_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                    return True
                except Exception as e:
                    logger.error(f"Error deleting local file: {str(e)}")
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
            # Generate S3 URL
            return f"{self.s3_location}/{file_path}"
        else:
            # For local files, return the static URL
            return f"/static/{file_path}"
