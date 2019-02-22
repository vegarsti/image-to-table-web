import boto3
import botocore
import uuid
import json


def put_image_in_bucket(unique_id, image_binary_data):
    full_filepath = make_filepath(unique_id)
    bucket_name = "vegarsti"
    s3 = boto3.resource("s3")
    s3.Bucket(bucket_name).put_object(
        Key=full_filepath,
        Body=image_binary_data,
        ContentType="image",
        ACL="public-read",
    )


def make_filepath(unique_id):
    folder = unique_id[:2]
    subfolder = unique_id[2:4]
    full_filepath = f"{folder}/{subfolder}/{unique_id}"
    return full_filepath


def get_url(unique_id):
    bucket_name = "vegarsti"
    full_filepath = make_filepath(unique_id)
    url = f"https://{bucket_name}.s3.amazonaws.com/{full_filepath}"
    return url
