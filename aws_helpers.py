import boto3
import os
from dotenv import load_dotenv

load_dotenv()
AWS_SERVER_PUBLIC_KEY = os.getenv("AWS_SERVER_PUBLIC_KEY")
AWS_SERVER_SECRET_KEY = os.getenv("AWS_SERVER_SECRET_KEY")


def filename_helper(filename):
    splitted = filename.rsplit(".")
    file_ending = splitted[-1]
    filename = ".".join(splitted[:-1])
    return filename, file_ending


def get_bucket_name():
    return "vegarsti"


def put_image_in_bucket(unique_id, image_binary_data, file_ending, filename):
    full_filepath = make_filepath(unique_id, filename) + "." + file_ending
    bucket_name = get_bucket_name()
    s3 = gets3()
    s3.Bucket(bucket_name).put_object(
        Key=full_filepath,
        Body=image_binary_data,
        ContentType="image",
        ACL="public-read",
    )


def put_excel_file_in_bucket(unique_id, excel_binary_data, filename):
    full_filepath = make_filepath(unique_id, filename) + ".xlsx"
    bucket_name = get_bucket_name()
    s3 = gets3()
    s3.Bucket(bucket_name).put_object(
        Key=full_filepath,
        Body=excel_binary_data,
        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ACL="public-read",
    )


def put_csv_file_in_bucket(unique_id, csv_binary_data, filename):
    full_filepath = make_filepath(unique_id, filename) + ".csv"
    bucket_name = get_bucket_name()
    s3 = gets3()
    s3.Bucket(bucket_name).put_object(
        Key=full_filepath,
        Body=csv_binary_data,
        ContentType="text/csv",
        ACL="public-read",
    )


def make_filepath(unique_id, filename):
    full_filepath = f"{unique_id}/{filename}"
    return full_filepath


def get_url(unique_id, filename):
    bucket_name = get_bucket_name()
    full_filepath = make_filepath(unique_id, filename)
    url = f"https://{bucket_name}.s3.amazonaws.com/{full_filepath}"
    return url


def get_url_with_file_ending(unique_id, file_ending, filename):
    bucket_name = get_bucket_name()
    full_filepath = make_filepath(unique_id, filename)
    url = f"https://{bucket_name}.s3.amazonaws.com/{full_filepath}.{file_ending}"
    return url


def get_excel_url(unique_id, filename):
    return get_url_with_file_ending(unique_id, "xlsx", filename)


def get_csv_url(unique_id, filename):
    return get_url_with_file_ending(unique_id, "csv", filename)


def delete_all_files_for_image(unique_id):
    bucket_name = get_bucket_name()
    s3 = gets3()
    objects_to_delete = s3.meta.client.list_objects(
        Bucket=bucket_name, Prefix=unique_id
    )
    delete_keys = {"Objects": []}
    delete_keys["Objects"] = [
        {"Key": k}
        for k in [obj["Key"] for obj in objects_to_delete.get("Contents", [])]
    ]
    s3.meta.client.delete_objects(Bucket=bucket_name, Delete=delete_keys)


def gets3():
    session = boto3.Session(
        aws_access_key_id=AWS_SERVER_PUBLIC_KEY,
        aws_secret_access_key=AWS_SERVER_SECRET_KEY,
    )
    s3 = session.resource("s3")
    return s3


def delete_remote_excel(unique_id, filename):
    bucket_name = get_bucket_name()
    s3 = gets3()
    filename_without_ending, _ = filename_helper(filename)
    excel_path = make_filepath(unique_id, filename_without_ending) + ".xlsx"
    excel_file = s3.Object(bucket_name, excel_path)
    excel_file.delete()
