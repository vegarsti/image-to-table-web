import boto3
import botocore


def create_bucket(bucket_name):
    s3 = boto3.resource("s3")
    s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
    )


def put_image_file_in_bucket(bucket_name, local_filename, remote_filename):
    s3 = boto3.resource("s3")
    image_binary_data = open(local_filename, "rb").read()
    s3.Bucket(bucket_name).put_object(
        Key=remote_filename,
        Body=image_binary_data,
        ContentType="image",
        ACL="public-read",
    )
    url = f"{bucket_name}.s3.amazonaws.com/{remote_filename}"
    return url


def get_image_file_from_bucket(bucket_name, remote_filename):
    s3 = boto3.resource("s3")
    downloaded_image_binary_data = (
        s3.Object(bucket_name, remote_filename).get()["Body"].read()
    )
    # downloaded_image_binary_data == image_binary_data
    # where image_binary_data is like above
    return downloaded_image_binary_data


def delete_file_in_bucket(bucket_name, remote_filename):
    s3 = boto3.resource("s3")
    response = s3.Object(bucket_name, remote_filename).delete()
    return response


def delete_bucket(bucket_name):
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(bucket_name)
    exists = True
    try:
        s3.meta.client.head_bucket(Bucket=bucket_name)
    except botocore.exceptions.ClientError as e:
        # If a client error is thrown, then check that it was a 404 error.
        # If it was a 404 error, then the bucket does not exist.
        error_code = e.response["Error"]["Code"]
        if error_code == "404":
            exists = False

    if exists:
        for key in bucket.objects.all():
            key.delete()
        bucket.delete()


def main():
    bucket_name = "vegarsti"
    delete_bucket(bucket_name)
    # create_bucket(bucket_name)
    # local_filename = "images/kapital-small.png"
    # remote_filename = "lol.png"
    # url = put_image_file_in_bucket(bucket_name, local_filename, remote_filename)
    # print(url)

    # Print name of all buckets
    """
    s3 = boto3.resource("s3")
    for bucket in s3.buckets.all():
        print(bucket.name)
    """


if __name__ == "__main__":
    main()
