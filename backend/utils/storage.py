import os
from minio import Minio
from io import BytesIO
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

minio_client = Minio(
    os.getenv("MINIO_ENDPOINT", "localhost:9000"),
    access_key=os.getenv("MINIO_ACCESS_KEY", "admin"),
    secret_key=os.getenv("MINIO_SECRET_KEY", "password123"),
    secure=False
)

bucket_name = os.getenv("S3_BUCKET", "jobagent-files")

if not minio_client.bucket_exists(bucket_name):
    minio_client.make_bucket(bucket_name)

def upload_file(file_name: str, file_bytes: bytes, content_type: str):
    """Saves a file and returns a temporary VIP link to download it."""
    minio_client.put_object(
        bucket_name,
        file_name,
        data=BytesIO(file_bytes),
        length=len(file_bytes),
        content_type=content_type
    )
    
    # Generate a temporary access URL valid for 7 days
    url = minio_client.presigned_get_object(
        bucket_name, 
        file_name, 
        expires=timedelta(days=7)
    )
    return url