import boto3
import os
from botocore.exceptions import NoCredentialsError, ClientError
from pathlib import Path

class S3Service:
    @staticmethod
    def get_client():
        kwargs = {}
        access_key = os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        region = os.getenv('AWS_REGION')
        
        if access_key:
            kwargs['aws_access_key_id'] = access_key
        if secret_key:
            kwargs['aws_secret_access_key'] = secret_key
        if region:
            kwargs['region_name'] = region
            
        return boto3.client('s3', **kwargs)

    @staticmethod
    def upload_file(file_content, object_name, content_type=None):
        """
        Upload a file to an S3 bucket
        :param file_content: Bytes of the file
        :param object_name: S3 object name (path in bucket)
        :param content_type: MIME type of the file
        :return: Public URL of the uploaded file
        """
        bucket_name = os.getenv('AWS_BUCKET_NAME')
        region = os.getenv('AWS_REGION')
        
        if not bucket_name:
            print("S3 Error: AWS_BUCKET_NAME is not set")
            return None
        if not region:
            print("S3 Error: AWS_REGION is not set")
            return None
        if file_content is None:
            print("S3 Error: file_content is None")
            return None
        if object_name is None:
            print("S3 Error: object_name is None")
            return None

        try:
            s3_client = S3Service.get_client()
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            s3_client.put_object(
                Bucket=bucket_name,
                Key=object_name,
                Body=file_content,
                **extra_args
            )
            
            url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{object_name}"
            return url
        except Exception as e:
            print(f"S3 Upload Error: {e}")
            # Log more details if it's a TypeError (NoneType issue)
            if isinstance(e, TypeError):
                print(f"Debug Info - Bucket: {bucket_name}, Key: {object_name}, Region: {region}")
            return None

    @staticmethod
    def delete_file(object_name):
        """
        Delete a file from an S3 bucket
        :param object_name: S3 object name (path in bucket)
        """
        bucket_name = os.getenv('AWS_BUCKET_NAME')
        if not bucket_name:
            print("S3 Error: AWS_BUCKET_NAME is not set")
            return False
            
        try:
            s3_client = S3Service.get_client()
            s3_client.delete_object(Bucket=bucket_name, Key=object_name)
            return True
        except Exception as e:
            print(f"S3 Delete Error: {e}")
            return False
