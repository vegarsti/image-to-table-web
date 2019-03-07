import boto3


def get_bucket_name():
    return "vegarsti"


def put_image_in_bucket(unique_id, image_binary_data, file_ending, filename):
    full_filepath = make_filepath(unique_id, filename) + "." + file_ending
    bucket_name = get_bucket_name()
    s3 = boto3.resource("s3")
    s3.Bucket(bucket_name).put_object(
        Key=full_filepath,
        Body=image_binary_data,
        ContentType="image",
        ACL="public-read",
    )


def put_excel_file_in_bucket(unique_id, excel_binary_data, filename):
    full_filepath = make_filepath(unique_id, filename) + ".xlsx"
    bucket_name = get_bucket_name()
    s3 = boto3.resource("s3")
    s3.Bucket(bucket_name).put_object(
        Key=full_filepath,
        Body=excel_binary_data,
        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ACL="public-read",
    )


def make_filepath(unique_id, filename):
    full_filepath = f"{unique_id}/{filename}"
    return full_filepath


def make_file_directory(unique_id):
    folder = unique_id[:2]
    subfolder = unique_id[2:4]
    full_filepath = f"{folder}/{subfolder}/{unique_id}"
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
    s3 = boto3.resource("s3")
    directory_path = make_file_directory(unique_id)
    directory = s3.Object(bucket_name, directory_path)
    directory.delete()


def delete_remote_excel(unique_id, filename):
    bucket_name = get_bucket_name()
    s3 = boto3.resource("s3")
    filename_without_ending = filename.rsplit(".")[0]
    print(filename_without_ending)
    excel_path = make_filepath(unique_id, filename_without_ending) + ".xlsx"
    print(excel_path)
    excel_file = s3.Object(bucket_name, excel_path)
    excel_file.delete()
