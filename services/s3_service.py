import boto3
import os
from botocore.exceptions import NoCredentialsError, ClientError
from pathlib import Path

class S3Service:
    @staticmethod
    def get_client():
        return boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )

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
        s3_client = S3Service.get_client()
        
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            # Note: Depending on bucket settings, you might need ACL='public-read'
            # But many modern buckets prefer block public access + CloudFront or signed URLs
            # For simplicity, we'll assume the bucket allows public read or is configured for it
            s3_client.put_object(
                Bucket=bucket_name,
                Key=object_name,
                Body=file_content,
                **extra_args
            )
            
            region = os.getenv('AWS_REGION')
            url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{object_name}"
            return url
        except Exception as e:
            print(f"S3 Upload Error: {e}")
            return None

    @staticmethod
    def delete_file(object_name):
        """
        Delete a file from an S3 bucket
        :param object_name: S3 object name (path in bucket)
        """
        bucket_name = os.getenv('AWS_BUCKET_NAME')
        s3_client = S3Service.get_client()
        
        try:
            s3_client.delete_object(Bucket=bucket_name, Key=object_name)
            return True
        except Exception as e:
            print(f"S3 Delete Error: {e}")
            return False
