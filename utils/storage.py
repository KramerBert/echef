import os
import boto3
from botocore.exceptions import ClientError
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class FileStorage:
    """Handle file storage operations (local or S3)"""
    
    def __init__(self, app=None):
        self.app = app
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app configuration"""
        self.app = app
        self.use_s3 = app.config.get('USE_S3', False)
        
        if self.use_s3:
            self.s3_bucket = app.config.get('S3_BUCKET')
            self.s3_location = app.config.get('S3_LOCATION')
            self.s3_key = app.config.get('S3_KEY')
            self.s3_secret = app.config.get('S3_SECRET')
            
            if not all([self.s3_bucket, self.s3_location, self.s3_key, self.s3_secret]):
                logger.warning("S3 configuration is incomplete. Check S3_BUCKET, S3_LOCATION, S3_KEY, S3_SECRET")
    
    def save_file(self, file_obj, path):
        """Save a file to storage (S3 or local)"""
        if self.use_s3:
            try:
                # Create S3 client
                s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=self.s3_key,
                    aws_secret_access_key=self.s3_secret
                )
                
                # Fix for the double filename issue - ensure the path doesn't already include the filename
                # Check if the file_obj has a filename attribute and if it's part of the path
                if hasattr(file_obj, 'filename') and file_obj.filename:
                    # Ensure we don't append the filename if it's already in the path
                    if path.endswith(file_obj.filename) or '/' + file_obj.filename in path:
                        s3_path = path
                    else:
                        # If path is a directory (ends with /), append the filename
                        if path.endswith('/'):
                            s3_path = path + file_obj.filename
                        else:
                            # Otherwise, use the path as is (it should already include the filename)
                            s3_path = path
                else:
                    s3_path = path
                
                logger.debug(f"Uploading file to S3 path: {s3_path}")
                
                # Upload the file
                s3_client.upload_fileobj(
                    file_obj,
                    self.s3_bucket,
                    s3_path,
                    ExtraArgs={
                        "ContentType": file_obj.content_type if hasattr(file_obj, 'content_type') else 'application/octet-stream'
                    }
                )
                
                return s3_path
            except Exception as e:
                logger.error(f"Error uploading file to S3: {str(e)}")
                raise e
        else:
            try:
                # Ensure directories exist
                os.makedirs(os.path.join(self.app.root_path, 'static', os.path.dirname(path)), exist_ok=True)
                
                # Save file locally
                local_path = os.path.join(self.app.root_path, 'static', path)
                file_obj.save(local_path)
                
                return path
            except Exception as e:
                logger.error(f"Error saving file locally: {str(e)}")
                raise e
    
    def delete_file(self, path):
        """Delete a file from storage"""
        if not path:
            return False
            
        if self.use_s3:
            try:
                s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=self.s3_key,
                    aws_secret_access_key=self.s3_secret
                )
                
                s3_client.delete_object(
                    Bucket=self.s3_bucket,
                    Key=path
                )
                
                return True
            except Exception as e:
                logger.error(f"Error deleting file from S3: {str(e)}")
                return False
        else:
            try:
                local_path = os.path.join(self.app.root_path, 'static', path)
                if os.path.exists(local_path):
                    os.remove(local_path)
                    return True
                return False
            except Exception as e:
                logger.error(f"Error deleting local file: {str(e)}")
                return False
    
    def get_file_url(self, path):
        """Get URL for a file"""
        if not path:
            return None
            
        if self.use_s3:
            return f"{self.s3_location}/{path}"
        else:
            # For local files, return a relative URL
            return f"/static/{path}"
