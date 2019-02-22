import boto3
import botocore
import uuid
import json


def put_image_in_bucket(filename, image_binary_data):
    bucket_name = "vegarsti"
    s3 = boto3.resource("s3")
    """
    unique_title = uuid.uuid4().hex
    folder = unique_title[:2]
    subfolder = unique_title[2:4]
    full_filepath = f"{folder}/{subfolder}/{unique_title}"
    """
    full_filepath = filename
    s3.Bucket(bucket_name).put_object(
        Key=full_filepath,
        Body=image_binary_data,
        ContentType="image",
        ACL="public-read",
    )
    # bucket could be the hash of the user's email?
    url = f"{bucket_name}.s3.amazonaws.com/{full_filepath}"
    return url
